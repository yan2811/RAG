<!--
  用户管理页面（M9 系统管理）
  支持用户列表查询、新增、编辑、删除
-->
<template>
  <div class="user-management">
    <!-- 查询栏 -->
    <el-card style="margin-bottom: 16px;">
      <el-form :inline="true" :model="queryForm">
        <el-form-item label="用户名">
          <el-input v-model="queryForm.username" placeholder="搜索用户名" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryForm.status" placeholder="全部" clearable style="width: 140px;">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchUsers">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 + 表格 -->
    <el-card>
      <div style="margin-bottom: 16px;">
        <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
      </div>

      <el-table :data="tableData" border stripe v-loading="loading" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column label="角色" width="200">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role" size="small" style="margin-right: 4px;">
              {{ roleMap[role] || role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 16px; text-align: right;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增用户' : '编辑用户'"
      width="520px"
      @closed="resetDialogForm"
    >
      <el-form ref="dialogFormRef" :model="dialogForm" :rules="dialogRules" label-width="80px">
        <el-form-item label="用户名" prop="username" v-if="dialogMode === 'create'">
          <el-input v-model="dialogForm.username" placeholder="3-64 字符" />
        </el-form-item>
        <el-form-item label="密码" :prop="dialogMode === 'create' ? 'password' : undefined">
          <el-input v-model="dialogForm.password" type="password" placeholder="8-20 字符，含字母和数字" show-password />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="dialogForm.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="dialogForm.roleIds">
            <el-radio v-for="role in allRoles" :key="role.id" :value="role.id">
              {{ role.display_name }}
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submitDialog">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 用户管理页面
 * 权限要求：admin:users
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { getUsersApi, createUserApi, updateUserApi, deleteUserApi } from '@/api/admin'
import { getRolesApi } from '@/api/admin'

/** 角色中文映射 */
const roleMap: Record<string, string> = {
  super_admin: '超级管理员', admin: '管理员', user: '普通用户', guest: '访客',
}

/** 查询表单 */
const queryForm = reactive({ username: '', status: '' })

/** 分页 */
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

/** 表格 */
const tableData = ref<any[]>([])
const loading = ref(false)

/** 对话框 */
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogLoading = ref(false)
const editingUserId = ref<number | null>(null)
const dialogFormRef = ref<FormInstance>()
const dialogForm = reactive({ username: '', password: '', email: '', roleIds: null as number | null })

const dialogRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ min: 8, max: 20, message: '密码长度 8-20 字符', trigger: 'blur' }],
}

/** 所有角色 */
const allRoles = ref<any[]>([])

/**
 * 获取用户列表
 */
async function fetchUsers() {
  loading.value = true
  try {
    const res: any = await getUsersApi({
      page: pagination.page,
      page_size: pagination.pageSize,
      username: queryForm.username || undefined,
      status: queryForm.status || undefined,
    })
    if (res.code === 0) {
      tableData.value = res.data.items
      pagination.total = res.data.total
    }
  } finally {
    loading.value = false
  }
}

/**
 * 获取所有角色
 */
async function fetchRoles() {
  const res: any = await getRolesApi()
  if (res.code === 0) allRoles.value = res.data
}

/** 重置查询 */
function resetQuery() { queryForm.username = ''; queryForm.status = ''; fetchUsers() }

/** 打开新增对话框 */
function openCreateDialog() {
  dialogMode.value = 'create'
  editingUserId.value = null
  dialogForm.username = ''
  dialogForm.password = ''
  dialogForm.email = ''
  dialogForm.roleIds = null
  dialogVisible.value = true
}

/** 打开编辑对话框 */
function openEditDialog(row: any) {
  dialogMode.value = 'edit'
  editingUserId.value = row.id
  dialogForm.username = row.username
  dialogForm.password = ''
  dialogForm.email = row.email || ''
  const role = allRoles.value.find(r => row.roles?.includes(r.name))
  dialogForm.roleIds = role ? role.id : null
  dialogVisible.value = true
}

/** 提交对话框 */
async function submitDialog() {
  if (!dialogFormRef.value) return
  await dialogFormRef.value.validate(async (valid) => {
    if (!valid) return
    dialogLoading.value = true
    try {
      const data: any = { email: dialogForm.email || undefined, role_ids: dialogForm.roleIds ? [dialogForm.roleIds] : [] }
      if (dialogMode.value === 'create') {
        data.username = dialogForm.username
        data.password = dialogForm.password
        await createUserApi(data)
        ElMessage.success('用户创建成功')
      } else {
        if (dialogForm.password) data.password = dialogForm.password
        await updateUserApi(editingUserId.value!, data)
        ElMessage.success('用户更新成功')
      }
      dialogVisible.value = false
      fetchUsers()
    } finally {
      dialogLoading.value = false
    }
  })
}

/** 删除用户 */
async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？此操作不可撤销。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
  })
  await deleteUserApi(row.id)
  ElMessage.success('用户已删除')
  fetchUsers()
}

/** 重置对话框表单 */
function resetDialogForm() {
  dialogFormRef.value?.resetFields()
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>
