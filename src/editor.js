import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, dropCursor, rectangularSelection, crosshairCursor, highlightActiveLine } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
import { defaultHighlightStyle, syntaxHighlighting, indentOnInput, bracketMatching, foldGutter, foldKeymap } from '@codemirror/language';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search';
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete';
import { lintKeymap } from '@codemirror/lint';
import { oneDark } from '@codemirror/theme-one-dark';
import { json } from '@codemirror/lang-json';
import { StreamLanguage } from '@codemirror/language';
import { ini } from '@codemirror/legacy-modes/mode/ini.js';
import { nginx } from '@codemirror/legacy-modes/mode/nginx.js';
import { indentWithTab } from '@codemirror/commands';

// Create language compartment for dynamic switching
const languageConf = new Compartment();

// Create editor instance
let editorView = null;
let currentFile = null;

// File type configurations
const fileTypes = {
  'content.json': {
    extension: json(),
    endpoint: {
      get: '/api/content',
      post: '/api/upload',
      format: 'json'
    }
  },
  'Caddyfile': {
    extension: StreamLanguage.define(nginx),
    endpoint: {
      get: '/admin/caddyfile',
      post: '/admin/caddyfile',
      format: 'text'
    }
  }
};

function initEditor(element) {
  const startState = EditorState.create({
    doc: '',
    extensions: [
      lineNumbers(),
      highlightActiveLineGutter(),
      highlightSpecialChars(),
      history(),
      foldGutter(),
      drawSelection(),
      dropCursor(),
      EditorState.allowMultipleSelections.of(true),
      indentOnInput(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      bracketMatching(),
      closeBrackets(),
      autocompletion(),
      rectangularSelection(),
      crosshairCursor(),
      highlightActiveLine(),
      highlightSelectionMatches(),
      keymap.of([
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        ...lintKeymap,
        indentWithTab
      ]),
      EditorView.lineWrapping,
      oneDark,
      languageConf.of([])
    ]
  });

  editorView = new EditorView({
    state: startState,
    parent: element
  });
}

async function loadFile(fileName) {
  if (!fileTypes[fileName]) {
    console.error('Unknown file type:', fileName);
    return;
  }

  currentFile = fileName;
  const config = fileTypes[fileName];

  try {
    const response = await fetch(config.endpoint.get);
    let content;

    if (config.endpoint.format === 'json') {
      const data = await response.json();
      content = JSON.stringify(data, null, 2);
    } else {
      content = await response.text();
    }

    // Update editor content and language
    editorView.dispatch({
      changes: {
        from: 0,
        to: editorView.state.doc.length,
        insert: content
      },
      effects: languageConf.reconfigure(config.extension)
    });

    updateStatus(fileName, '');
  } catch (error) {
    console.error('Error loading file:', error);
    updateStatus(fileName, 'Error loading file');
  }
}

async function saveFile() {
  if (!currentFile || !fileTypes[currentFile]) {
    console.error('No file selected');
    return;
  }

  const config = fileTypes[currentFile];
  const content = editorView.state.doc.toString();

  try {
    let requestConfig;

    if (config.endpoint.format === 'json') {
      // Validate JSON before sending
      try {
        JSON.parse(content);
      } catch (e) {
        updateStatus(currentFile, 'Invalid JSON: ' + e.message);
        return;
      }

      requestConfig = {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'content=' + encodeURIComponent(content)
      };
    } else {
      requestConfig = {
        method: 'POST',
        body: content
      };
    }

    const response = await fetch(config.endpoint.post, requestConfig);

    if (!response.ok) {
      throw new Error('Failed to save');
    }

    const result = await response.json();

    if (currentFile === 'Caddyfile') {
      updateStatus(currentFile, 'Saved. Restart Caddy Required.');
    } else {
      updateStatus(currentFile, 'Saved successfully.');
    }

    // Refresh backups
    if (window.refreshBackups) window.refreshBackups();
    if (window.refreshCaddyfileBackups) window.refreshCaddyfileBackups();

  } catch (error) {
    console.error('Error saving file:', error);
    updateStatus(currentFile, 'Error saving file');
  }
}

function updateStatus(fileName, message) {
  const statusId = fileName === 'content.json' ? 'content-status' : 'caddyfile-status';
  const statusElement = document.getElementById(statusId);
  if (statusElement) {
    statusElement.textContent = message;
  }
}

function downloadFile() {
  if (!currentFile) return;

  const content = editorView.state.doc.toString();
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = currentFile;
  a.click();
  URL.revokeObjectURL(url);
}

// Export functions for global access
window.CaddyEditor = {
  init: initEditor,
  loadFile,
  saveFile,
  downloadFile
};
