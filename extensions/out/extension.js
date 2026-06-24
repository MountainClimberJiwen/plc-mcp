"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
// Make sure to run 'npm install' to install the necessary dependencies, including the 'vscode' module.
const vscode = __importStar(require("vscode"));
// @ts-ignore
const fetch = require('node-fetch');
function activate(context) {
    let runSclStatusBarItem;
    function updateStatusBarItem() {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'scl') {
            runSclStatusBarItem.show();
        }
        else {
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
    let disposable = vscode.commands.registerCommand('scl-runner.runScl', (uri) => __awaiter(this, void 0, void 0, function* () {
        var _a, _b;
        let filePath = '';
        if (uri && uri.fsPath) {
            filePath = uri.fsPath;
        }
        else if (vscode.window.activeTextEditor) {
            filePath = vscode.window.activeTextEditor.document.uri.fsPath;
        }
        // remve the content root from filePath
        const contentRoot = (_b = (_a = vscode.workspace.workspaceFolders) === null || _a === void 0 ? void 0 : _a[0]) === null || _b === void 0 ? void 0 : _b.uri.fsPath;
        // const contentRoot = "e:\\openess\\scl";
        const relativePath = filePath.replace(contentRoot + '\\', '');
        try {
            const url = `http://localhost:8080/ping?path=${encodeURIComponent(relativePath)}`;
            const response = yield fetch(url);
            const data = yield response.json();
            vscode.window.showInformationMessage('relativePath: ' + relativePath +
                ' filePath: ' + filePath +
                ' contentRoot: ' + contentRoot);
            ' PLC Response: ' + JSON.stringify(data);
        }
        catch (error) {
            vscode.window.showErrorMessage('Failed to contact PLC: ' + error);
        }
    }));
    context.subscriptions.push(disposable);
}
exports.activate = activate;
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map