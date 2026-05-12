import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { Component } from 'vue'

export function mountComponent(component: Component, options: Record<string, any> = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)

  return mount(component, {
    global: {
      plugins: [pinia, ElementPlus],
      stubs: {
        'el-dialog': { template: '<div><slot /></div>', props: ['modelValue'] },
        'el-form': { template: '<form><slot /></form>', props: ['model'] },
        'el-form-item': { template: '<div><slot /></div>', props: ['label', 'prop'] },
        'el-input': { template: '<input />', props: ['modelValue'] },
        'el-select': { template: '<select />', props: ['modelValue'] },
        'el-option': { template: '<option />', props: ['label', 'value'] },
        'el-button': { template: '<button><slot /></button>', props: ['type', 'loading'] },
        'el-table': { template: '<table><slot /></table>', props: ['data'] },
        'el-table-column': { template: '<td><slot /></td>', props: ['label', 'prop'] },
        'el-tag': { template: '<span><slot /></span>', props: ['type'] },
        'el-pagination': { template: '<div />', props: ['total'] },
      },
    },
    ...options,
  })
}

export async function flushPromises() {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

export function mockApiResponse(data: any, code = 0, message = 'success') {
  return { code, message, data }
}

export function createMockRouter() {
  return {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    currentRoute: { value: { query: {}, params: {} } },
  }
}
