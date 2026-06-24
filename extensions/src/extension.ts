// Make sure to run 'npm install' to install the necessary dependencies, including the 'vscode' module.
import * as vscode from 'vscode';
// @ts-ignore
const fetch = require('node-fetch');

export function activate(context: vscode.ExtensionContext) {
  let runSclStatusBarItem: vscode.StatusBarItem;

  function updateStatusBarItem() {
    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.languageId === 'scl') {
      runSclStatusBarItem.show();
    } else {
      runSclStatusBarItem.hide();
    }
  }

  runSclStatusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  runSclStatusBarItem.command = 'scl-runner.runScl';
  runSclStatusBarItem.text = '$(triangle-right) Run SCL';
  runSclStatusBarItem.tooltip = 'Run SCL File';
  context.subscriptions.push(runSclStatusBarItem);

  vscode.window.onDidChangeActiveTextEditor(updateStatusBarItem, null, context.subscriptions);
  vscode.workspace.onDidOpenTextDocument(updateStatusBarItem, null, context.subscriptions);

  updateStatusBarItem();

  let disposable = vscode.commands.registerCommand('scl-runner.runScl', async (uri?: vscode.Uri) => {
    let filePath = '';
    if (uri && uri.fsPath) {
      filePath = uri.fsPath;
    } else if (vscode.window.activeTextEditor) {
      filePath = vscode.window.activeTextEditor.document.uri.fsPath;
    }
    // remve the content root from filePath
    const contentRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    // const contentRoot = "e:\\openess\\scl";
    const relativePath = filePath.replace(contentRoot + '\\', '');
    try {
      const url = `http://localhost:8080/ping?path=${encodeURIComponent(relativePath)}`;
      const response = await fetch(url);
      const data = await response.json();
      vscode.window.showInformationMessage('relativePath: ' + relativePath +
        ' filePath: ' + filePath + 
        ' contentRoot: ' + contentRoot)
        ' PLC Response: ' + JSON.stringify(data);
    } catch (error) {
      vscode.window.showErrorMessage('Failed to contact PLC: ' + error);
    }
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {} 