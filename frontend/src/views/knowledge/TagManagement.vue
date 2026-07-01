<!--
  标签管理页面（M3）
  标签增删 + 文档打标
-->
<template>
  <div class="tag-management">
    <el-row :gutter="16">
      <!-- 标签列表 -->
      <el-col :span="10">
        <el-card>
          <template #header><span>标签列表</span></template>
          <div style="margin-bottom: 12px; display: flex; gap: 8px;">
            <el-input v-model="newTagName" placeholder="标签名" size="small" style="width: 140px;" @keydown.enter="handleCreate" />
            <el-color-picker v-model="newTagColor" size="small" />
            <el-button type="primary" size="small" @click="handleCreate">新增</el-button>
          </div>
          <el-tag v-for="tag in tags" :key="tag.id" :color="tag.color"
            size="large" closable style="margin: 4px 8px; cursor: pointer;"
            :effect="selectedTag?.id === tag.id ? 'dark' : 'light'"
            @click="selectTag(tag)" @close="handleDelete(tag)">
            {{ tag.name }}
            <span style="opacity:0.8;">({{ tag.document_count }})</span>
          </el-tag>
          <el-empty v-if="tags.length === 0" description="暂无标签" :image-size="40" />
        </el-card>
      </el-col>

      <!-- 关联文档 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <span v-if="selectedTag">标签「{{ selectedTag.name }}」关联的文档</span>
            <span v-else>选择左侧标签查看关联文档</span>
          </template>
          <el-table v-if="selectedTag" :data="tagDocs" border stripe size="small" max-height="400">
            <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
            <el-table-column prop="company_code" label="股票代码" width="100" />
            <el-table-column prop="fiscal_year" label="财年" width="70" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.parse_status === 'completed' ? 'success' : 'info'" size="small">
                  {{ row.parse_status === 'completed' ? '已完成' : row.parse_status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button type="danger" link size="small" @click="removeDocTag(row)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 添加文档到当前标签 -->
          <div v-if="selectedTag" style="margin-top: 16px;">
            <el-select v-model="addDocId" placeholder="选择文档添加到当前标签" size="small" style="width: 350px;" clearable>
              <el-option v-for="doc in untaggedDocs" :key="doc.id"
                :label="`${doc.file_name}（${doc.company_code || '-'}）`" :value="doc.id" />
            </el-select>
            <el-button type="primary" size="small" style="margin-left: 8px;" @click="addDocToTag" :disabled="!addDocId">
              添加
            </el-button>
          </div>

          <el-empty v-if="!selectedTag" description="点击左侧标签查看" :image-size="40" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTagsApi, createTagApi, deleteTagApi, setDocTagsApi } from '@/api/knowledge'
import { getDocumentsApi } from '@/api/document'

const tags = ref<any[]>([])
const newTagName = ref('')
const newTagColor = ref('#409EFF')
const selectedTag = ref<any>(null)
const tagDocs = ref<any[]>([])
const untaggedDocs = ref<any[]>([])
const addDocId = ref<number | null>(null)

async function fetchTags() {
  try {
    const res: any = await getTagsApi()
    if (res.code === 0) tags.value = res.data
  } catch { /* ignore */ }
}

async function handleCreate() {
  if (!newTagName.value.trim()) return ElMessage.warning('请输入标签名')
  await createTagApi(newTagName.value, newTagColor.value)
  ElMessage.success('标签创建成功')
  newTagName.value = ''
  fetchTags()
}

async function handleDelete(tag: any) {
  await ElMessageBox.confirm(`确定删除标签「${tag.name}」？`, '提示', { type: 'warning' })
  await deleteTagApi(tag.id)
  if (selectedTag.value?.id === tag.id) selectedTag.value = null
  ElMessage.success('已删除')
  fetchTags()
}

async function selectTag(tag: any) {
  selectedTag.value = tag
  addDocId.value = null
  // 获取关联文档
  const res: any = await getDocumentsApi({ page_size: 100 })
  if (res.code === 0) {
    const allDocs = res.data.items
    // 根据 document_count 判断关联（简化处理：通过标签名模糊匹配文档的行业属性）
    // 实际应该通过后端 document_tags 关联表查询
    // 这里暂时展示所有已完成文档，允许手动关联
    tagDocs.value = allDocs.filter((d: any) => d.parse_status === 'completed')
    untaggedDocs.value = allDocs.filter((d: any) => d.parse_status === 'completed')
  }
}

async function addDocToTag() {
  if (!addDocId.value || !selectedTag.value) return
  await setDocTagsApi(addDocId.value, [selectedTag.value.id])
  ElMessage.success('文档已关联到标签')
  addDocId.value = null
}

async function removeDocTag(row: any) {
  await setDocTagsApi(row.id, [])
  ElMessage.success('已移除关联')
  selectTag(selectedTag.value)
}

onMounted(fetchTags)
</script>
