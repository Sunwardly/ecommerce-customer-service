import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'node_modules/**', 'vue-demo/**', 'playwright-report/**', 'test-results/**'] },
  ...vue.configs['flat/essential'],
  {
    files: ['**/*.js', '**/*.vue'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    rules: {
      'no-undef': 'error',
      'no-unreachable': 'error',
      'no-constant-condition': 'error',
      'no-console': ['error', { allow: ['warn', 'error'] }],
    },
  },
]
