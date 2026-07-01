<!--
  文档上传页面（M1）
  支持拖拽上传、文件信息填写、上传进度展示
-->
<template>
  <div class="document-upload">
    <el-card>
      <template #header>
        <el-page-header @back="$router.push('/documents')" title="返回文档列表">
          <template #content><span>上传财报 PDF</span></template>
        </el-page-header>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 600px;">
        <!-- 文件选择区域 -->
        <el-form-item label="选择文件" prop="file">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :before-upload="() => false"
            accept=".pdf"
            drag
          >
            <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将 PDF 文件拖拽到此处，或<em>点击选择</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                仅支持 PDF 格式，单个文件不超过 100MB
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 文件信息 -->
        <el-form-item label="股票代码" prop="company_code">
          <el-input v-model="form.company_code" placeholder="如 002594（比亚迪）" maxlength="16" />
        </el-form-item>

        <el-form-item label="财年" prop="fiscal_year">
          <el-input-number v-model="form.fiscal_year" :min="2000" :max="2030" placeholder="如 2024" />
        </el-form-item>

        <el-form-item label="季度" prop="fiscal_quarter">
          <el-select v-model="form.fiscal_quarter">
            <el-option :value="4" label="年报（Q4）" />
            <el-option :value="1" label="一季报（Q1）" />
            <el-option :value="2" label="中报（Q2）" />
            <el-option :value="3" label="三季报（Q3）" />
          </el-select>
        </el-form-item>

        <el-form-item label="报告类型">
          <el-select v-model="form.doc_type">
            <el-option value="annual_report" label="年报" />
            <el-option value="quarterly_report" label="季报" />
            <el-option value="prospectus" label="招股书" />
            <el-option value="audit_report" label="审计报告" />
            <el-option value="other" label="其他" />
          </el-select>
        </el-form-item>

        <!-- 提交按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!selectedFile"
            size="large"
            @click="handleUpload"
          >
            <el-icon><Upload /></el-icon>
            {{ uploading ? '上传解析中...' : '上传并解析' }}
          </el-button>
          <span v-if="uploading" style="margin-left: 12px; color: #909399; font-size: 13px;">
            {{ progressText }}
          </span>
        </el-form-item>
      </el-form>

      <!-- 上传结果 -->
      <el-alert
        v-if="uploadResult"
        :title="uploadResult.msg"
        :type="uploadResult.success ? 'success' : 'error'"
        :closable="false"
        show-icon
        style="margin-top: 16px;"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * 文档上传页面
 * 支持拖拽/选择 PDF 文件，填写元数据后上传并自动解析
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, UploadInstance, UploadFile } from 'element-plus'
import { uploadDocumentApi } from '@/api/document'

const router = useRouter()
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()

/** 选中的文件 */
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const progressText = ref('')
const uploadResult = ref<{ success: boolean; msg: string } | null>(null)

/** 表单数据 */
const form = reactive({
  company_code: '',
  fiscal_year: new Date().getFullYear(),
  fiscal_quarter: 4,
  doc_type: 'annual_report',
})

/** 校验规则 */
const rules = {}

/**
 * 文件选择变更
 */
function handleFileChange(file: UploadFile) {
  const rawFile = file.raw
  if (!rawFile) return
  if (!rawFile.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.error('仅支持 PDF 格式文件')
    uploadRef.value?.clearFiles()
    return
  }
  if (rawFile.size > 100 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 100MB')
    uploadRef.value?.clearFiles()
    return
  }
  selectedFile.value = rawFile
}

/** 文件移除 */
function handleFileRemove() {
  selectedFile.value = null
  uploadResult.value = null
}

/**
 * 上传文件并触发解析
 */
async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 PDF 文件')
    return
  }

  uploading.value = true
  progressText.value = '正在上传文件...'
  uploadResult.value = null

  try {
    // 构建 FormData
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    // 后端参数需要通过 FormData 传递
    formData.append('company_code', form.company_code || '')
    formData.append('fiscal_year', String(form.fiscal_year || ''))
    formData.append('fiscal_quarter', String(form.fiscal_quarter))
    formData.append('doc_type', form.doc_type)

    progressText.value = '文件上传中，正在解析...'

    const res: any = await uploadDocumentApi(formData)

    if (res.code === 0) {
      uploadResult.value = {
        success: true,
        msg: `上传成功！文档已自动解析，状态：${res.data.parse_status}`,
      }
      ElMessage.success('文档上传并解析完成')
      // 3 秒后跳转到文档列表
      setTimeout(() => router.push('/documents'), 2000)
    } else {
      uploadResult.value = { success: false, msg: res.msg || '上传失败' }
    }
  } catch (e: any) {
    uploadResult.value = {
      success: false,
      msg: e?.response?.data?.detail || '上传失败，请重试',
    }
  } finally {
    uploading.value = false
    progressText.value = ''
  }
}
</script>
