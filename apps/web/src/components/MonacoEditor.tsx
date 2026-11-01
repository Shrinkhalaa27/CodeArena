"use client";
// Monaco is bundled locally (not fetched from a CDN) so the editor works offline, behind strict
// CSP, and without a third-party runtime dependency. Workers fall back to the main thread, which
// is fine for syntax highlighting at this scale.
import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";

loader.config({ monaco });

export default Editor;
