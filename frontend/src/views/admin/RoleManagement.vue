<!--
  角色管理页面（M9）
  管理角色及其权限配置
-->
<template>
  <div class="role-management">
    <el-card>
      <div style="margin-bottom: 16px;">
        <el-button type="primary" @click="openCreateDialog">新增角色</el-button>
      </div>
      <el-table :data="roles" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="角色标识" width="140" />
        <el-table-column prop="display_name" label="显示名称" width="140" />
        <el-table-column label="权限列表" min-width="300">
          <template #default="{ row }">
            <el-tag v-for="perm in row.permissions" :key="perm" size="small" style="margin: 2px;">
              {{ perm }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增角色对话框 -->
    <el-dialog v-model="dialogVisible" title="新增角色" width="500px">
      <el-form :model="dialogForm" label-width="80px">
        <el-form-item label="角色标识">
          <el-input v-model="dialogForm.name" placeholder="如: editor" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="dialogForm.display_name" placeholder="如: 编辑者" />
        </el-form-item>
        <el-form-item label="权限列表">
          <el-checkbox-group v-model="dialogForm.permissions">
            <el-checkbox label="admin:users">用户管理</el-checkbox>
            <el-checkbox label="admin:roles">角色管理</el-checkbox>
            <el-checkbox label="admin:logs">操作日志</el-checkbox>
            <el-checkbox label="admin:settings">系统配置</el-checkbox>
            <el-checkbox label="doc:upload">文档上传</el-checkbox>
            <el-checkbox label="doc:delete">文档删除</el-checkbox>
            <el-checkbox label="doc:view">文档查看</el-checkbox>
            <el-checkbox label="kb:manage">知识库管理</el-checkbox>
            <el-checkbox label="kb:export">知识库导出</el-checkbox>
            <el-checkbox label="chat:use">智能问答</el-checkbox>
            <el-checkbox label="report:generate">报告生成</el-checkbox>
            <el-checkbox label="report:view">报告查看</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRolesApi, createRoleApi } from '@/api/admin'

const roles = ref<any[]>([])
const dialogVisible = ref(false)
const dialogForm = ref({ name: '', display_name: '', permissions: [] as string[] })

async function fetchRoles() {
  const res: any = await getRolesApi()
  if (res.code === 0) roles.value = res.data
}

function openCreateDialog() {
  dialogForm.value = { name: '', display_name: '', permissions: [] }
  dialogVisible.value = true
}

async function createRole() {
  const res: any = await createRoleApi(dialogForm.value)
  if (res.code === 0) {
    ElMessage.success('角色创建成功')
    dialogVisible.value = false
    fetchRoles()
  }
}

onMounted(fetchRoles)
</script>
