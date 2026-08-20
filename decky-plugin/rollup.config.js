import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
import replace from '@rollup/plugin-replace';

export default {
  input: 'src/index.tsx',
  output: {
    file: 'dist/index.js',
    format: 'iife',
    name: 'zotaque',
    exports: 'default',
    globals: {
      react: 'SP_REACT',
      'react-dom': 'SP_REACTDOM',
      'decky-frontend-lib': 'DFL',
    },
  },
  plugins: [
    replace({
      preventAssignment: true,
      'process.env.NODE_ENV': JSON.stringify('production'),
    }),
    resolve({
      browser: true,
    }),
    commonjs(),
    typescript({
      tsconfig: './tsconfig.json',
      noEmitOnError: false,
    }),
  ],
  external: ['react', 'react-dom', 'decky-frontend-lib'],
};
