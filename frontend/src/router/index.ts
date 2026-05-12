import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
        { path: 'cases', name: 'Cases', component: () => import('@/views/cases/CaseList.vue') },
        { path: 'tasks', name: 'Tasks', component: () => import('@/views/tasks/TaskList.vue') },
        { path: 'results', name: 'Results', component: () => import('@/views/results/ResultList.vue') },
        { path: 'nodes', name: 'Nodes', component: () => import('@/views/nodes/NodeList.vue') },
        { path: 'system', name: 'System', component: () => import('@/views/System.vue') },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
