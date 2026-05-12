import { config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'

const pinia = createPinia()
setActivePinia(pinia)

config.global.plugins = [pinia, ElementPlus]
