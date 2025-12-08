import * as esbuild from 'esbuild';

await esbuild.build({
  entryPoints: ['src/editor.js'],
  bundle: true,
  outfile: 'static/editor.bundle.js',
  format: 'iife',
  globalName: 'CaddyEditor',
  minify: true,
});

console.log('CodeMirror bundle created at static/editor.bundle.js');
