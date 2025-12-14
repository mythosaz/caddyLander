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
import { nginx } from '@codemirror/legacy-modes/mode/nginx';
import { indentWithTab } from '@codemirror/commands';

// Create language compartment for dynamic switching
const languageConf = new Compartment();

// Create editor instance
let editorView = null;
let currentFile = null;
const fileState = new Map();

function getOrCreateFileState(fileName) {
  if (!fileState.has(fileName)) {
    fileState.set(fileName, {
      lastSaved: '',
      isDirty: false,
      position: { line: 1, column: 1 }
    });
  }
  return fileState.get(fileName);
}

function setStatusLine(fileName) {
  const statusId = fileName === 'content.json' ? 'content-editor-status' : 'caddyfile-editor-status';
  const otherId = fileName === 'content.json' ? 'caddyfile-editor-status' : 'content-editor-status';
  const active = document.getElementById(statusId);
  const inactive = document.getElementById(otherId);

  if (active) active.style.display = 'flex';
  if (inactive) inactive.style.display = 'none';
}

function updateEditorStatusLine(fileName) {
  const status = getOrCreateFileState(fileName);
  const statusId = fileName === 'content.json' ? 'content-editor-status' : 'caddyfile-editor-status';
  const statusEl = document.getElementById(statusId);

  if (!statusEl) return;

  statusEl.textContent = `${fileName} · ${status.isDirty ? 'Dirty' : 'Saved'} · Ln ${status.position.line}, Col ${status.position.column}`;
}

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
      EditorView.updateListener.of((update) => {
        const fileState = getOrCreateFileState(currentFile || 'content.json');

        if (update.selectionSet) {
          const line = update.state.doc.lineAt(update.state.selection.main.head);
          fileState.position = {
            line: line.number,
            column: update.state.selection.main.head - line.from + 1
          };
          updateEditorStatusLine(currentFile || 'content.json');
        }

        if (update.docChanged) {
          const content = update.state.doc.toString();
          fileState.isDirty = content !== fileState.lastSaved;
          updateEditorStatusLine(currentFile || 'content.json');
        }
      }),
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
  const state = getOrCreateFileState(fileName);

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
    state.lastSaved = content;
    state.isDirty = false;
    editorView.dispatch({
      changes: {
        from: 0,
        to: editorView.state.doc.length,
        insert: content
      },
      effects: languageConf.reconfigure(config.extension)
    });

    const cursorLine = editorView.state.doc.lineAt(editorView.state.selection.main.head);
    state.position = { line: cursorLine.number, column: editorView.state.selection.main.head - cursorLine.from + 1 };
    setStatusLine(fileName);
    updateEditorStatusLine(fileName);

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

    // Handle new pipeline response format for Caddyfile
    if (currentFile === 'Caddyfile') {
      if (result.success === false) {
        // Pipeline failed at some stage
        const stageLabel = result.stage.charAt(0).toUpperCase() + result.stage.slice(1);
        updateStatus(currentFile, `${stageLabel} failed: ${result.output}`);
        return;
      } else if (result.success === true && result.stage === 'complete') {
        // Pipeline succeeded
        const serverMessage = result.message || 'Saved, validated, formatted. Reload Caddy to apply changes.';
        updateStatus(currentFile, serverMessage);
      } else {
        // Fallback for backward compatibility
        updateStatus(currentFile, 'Saved. Reload Caddy to apply changes.');
      }
    } else {
      updateStatus(currentFile, 'Saved successfully.');
    }

    // Refresh backups
    if (window.refreshBackups) window.refreshBackups();
    if (window.refreshCaddyfileBackups) window.refreshCaddyfileBackups();

    const state = getOrCreateFileState(currentFile);
    state.lastSaved = content;
    state.isDirty = false;
    updateEditorStatusLine(currentFile);

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
    statusElement.style.display = message ? 'block' : 'none';
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

function setContent(content) {
  if (!editorView) return;

  editorView.dispatch({
    changes: {
      from: 0,
      to: editorView.state.doc.length,
      insert: content
    }
  });
}

// Export functions for global access
window.CaddyEditor = {
  init: initEditor,
  loadFile,
  saveFile,
  downloadFile,
  setContent
};
