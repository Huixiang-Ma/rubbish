// 双端会话管理（无 pinia 依赖）：toC 游客端 与 toB 工作台 各自独立登录态
//   toC：wl_token    + wl_user        （traveler，手机验证码 / 账号密码 realm=toc）
//   toB：wl_admin_token + wl_admin_user（admin / supervisor / consultant，realm=tob）
// 两端 token 互不覆盖：登录工作台不再顶掉游客端会话，反之亦然。
// token 均为演示级 HMAC（u=用户名, r=角色, t=租户）；鉴权一律以服务端为准。
import { reactive } from 'vue'
import { authApi } from '../api/index.js'

const TOKEN_KEY = 'wl_token'
const USER_KEY = 'wl_user'
const ADMIN_TOKEN_KEY = 'wl_admin_token'
const ADMIN_USER_KEY = 'wl_admin_user'

const STAFF_ROLES = ['admin', 'supervisor', 'consultant']
const ROLE_LABEL = { admin: '管理员', supervisor: '主管', consultant: '顾问', traveler: '游客' }

function decodeUser(token) {
  try {
    const raw = token.split('.')[0].replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(escape(atob(raw)))
    const p = JSON.parse(json)
    return { username: p.u, role: p.r, tenant: p.t || null }
  } catch {
    return { username: '', role: 'traveler', tenant: null }
  }
}

function readStored(userKey, tokenKey) {
  try {
    const raw = localStorage.getItem(userKey)
    if (raw) {
      const u = JSON.parse(raw)
      if (u && localStorage.getItem(tokenKey)) return u
    }
  } catch { /* ignore */ }
  const token = localStorage.getItem(tokenKey)
  return token ? decodeUser(token) : null
}

export const auth = reactive({
  traveler: readStored(USER_KEY, TOKEN_KEY),
  admin: readStored(ADMIN_USER_KEY, ADMIN_TOKEN_KEY),
  get isLogin() { return !!localStorage.getItem(TOKEN_KEY) },
  get isStaff() {
    const a = this.admin
    return !!(a && a.role && STAFF_ROLES.includes(a.role) && localStorage.getItem(ADMIN_TOKEN_KEY))
  },
  roleLabel(role) { return ROLE_LABEL[role] || role || '访客' },
})

function saveSession(tokenKey, userKey, token, meta = {}) {
  localStorage.setItem(tokenKey, token)
  const user = { ...decodeUser(token), ...meta }
  localStorage.setItem(userKey, JSON.stringify(user))
  return user
}

export function clearTraveler() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  auth.traveler = null
}

export function clearAdmin() {
  localStorage.removeItem(ADMIN_TOKEN_KEY)
  localStorage.removeItem(ADMIN_USER_KEY)
  auth.admin = null
}

/* —— toC 游客端 —— */
export async function requestCode(phone) {
  return authApi.requestCode(phone)
}

export async function loginBySms(phone, code) {
  const res = await authApi.loginSms(phone, code)
  auth.traveler = saveSession(TOKEN_KEY, USER_KEY, res.token, { username: res.name || phone, role: res.role || 'traveler' })
  return auth.traveler
}

// 注册：手机号 + 短信验证码（服务端验码）+ 密码，账号即手机号；昵称选填
export async function registerUser(phone, password, display, smsCode) {
  const res = await authApi.register({ username: phone, phone, sms_code: smsCode, password, display })
  auth.traveler = saveSession(TOKEN_KEY, USER_KEY, res.token, { username: res.name || phone, role: res.role || 'traveler' })
  return auth.traveler
}

/** 找回密码：手机号+验证码重置后自动登录（后端返回新 token） */
export async function resetPasswordBySms(phone, smsCode, newPassword) {
  const res = await authApi.resetPassword(phone, smsCode, newPassword)
  return saveSession(TOKEN_KEY, USER_KEY, res.token, { username: res.name || phone, role: res.role || 'traveler' })
}

export async function loginByPassword(realm, username, password) {
  const res = await authApi.login(realm, username, password)
  if (realm === 'tob' || STAFF_ROLES.includes(res.role)) {
    auth.admin = saveSession(ADMIN_TOKEN_KEY, ADMIN_USER_KEY, res.token, { username: res.name || username, role: res.role, tenant: res.tenant })
    return auth.admin
  }
  auth.traveler = saveSession(TOKEN_KEY, USER_KEY, res.token, { username: res.name || username, role: res.role })
  return auth.traveler
}

/** 兼容旧调用名：游客端退出 */
export function logout() {
  clearTraveler()
}
