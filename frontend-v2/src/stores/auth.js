import { defineStore } from 'pinia'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('wl_token') || '',
    name: localStorage.getItem('wl_name') || '',
    role: localStorage.getItem('wl_role') || '',
  }),
  getters: {
    isLogged: (s) => !!s.token,
  },
  actions: {
    async login(realm, username, password) {
      const r = await authApi.login(realm, username, password)
      this.token = r.token
      this.name = r.name || username
      this.role = r.role || ''
      localStorage.setItem('wl_token', r.token)
      localStorage.setItem('wl_name', this.name)
      localStorage.setItem('wl_role', this.role)
      return r
    },
    logout() {
      this.token = ''
      this.name = ''
      this.role = ''
      localStorage.removeItem('wl_token')
      localStorage.removeItem('wl_name')
      localStorage.removeItem('wl_role')
    },
  },
})
