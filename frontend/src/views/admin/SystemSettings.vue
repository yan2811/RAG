<!--
  系统配置页面（M9）
  管理系统全局参数
-->
<template>
  <div class="system-settings">
    <el-card>
      <template #header><span>系统配置</span></template>
      <el-form label-width="160px">
        <el-form-item label="DeepSeek API Key">
          <el-input v-model="settings.deepseek_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="文本分块大小 (tokens)">
          <el-input-number v-model="settings.chunk_size" :min="200" :max="3000" :step="100" />
        </el-form-item>
        <el-form-item label="分块重叠 (tokens)">
          <el-input-number v-model="settings.chunk_overlap" :min="0" :max="500" :step="50" />
        </el-form-item>
        <el-form-item label="系统名称">
          <el-input v-model="settings.system_name" placeholder="财报 RAG 知识库系统" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettingsApi, updateSettingsApi } from '@/api/admin'

const settings = reactive<Record<string, any>>({
  deepseek_api_key: '',
  chunk_size: 1000,
  chunk_overlap: 200,
  system_name: '财报 RAG 知识库系统',
})

async function fetchSettings() {
  try {
    const res: any = await getSettingsApi()
    if (res.code === 0) {
      for (const key in res.data) {
        if (key in settings) settings[key] = res.data[key].value
      }
    }
  } catch { /* ignore */ }
}

async function saveSettings() {
  const res: any = await updateSettingsApi(settings)
  if (res.code === 0) ElMessage.success('配置保存成功')
}

onMounted(fetchSettings)
</script>
