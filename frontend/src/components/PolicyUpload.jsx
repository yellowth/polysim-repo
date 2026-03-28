import { useState } from "react";
import { Upload, FileText } from "lucide-react";

export default function PolicyUpload({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "txt", "md", "text"].includes(ext)) {
      alert("Please upload a PDF, TXT, or MD file");
      return;
    }
    setUploading(true);
    await onUpload(file);
    setUploading(false);
  };

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div
        className={`border-2 border-dashed rounded-2xl p-16 text-center max-w-lg w-full transition-colors
          ${dragging ? "border-emerald-400 bg-emerald-400/5" : "border-slate-700 hover:border-slate-500"}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
      >
        {uploading ? (
          <>
            <FileText className="w-12 h-12 mx-auto mb-4 text-emerald-400 animate-pulse" />
            <p className="text-slate-300">Parsing policy document...</p>
          </>
        ) : (
          <>
            <Upload className="w-12 h-12 mx-auto mb-4 text-slate-500" />
            <p className="text-lg text-slate-300 mb-2">Drop a policy document here</p>
            <p className="text-sm text-slate-500 mb-6">PDF, TXT, or Markdown</p>
            <input
              type="file"
              accept=".pdf,.txt,.md,.text"
              className="hidden"
              id="file-input"
              onChange={(e) => handleFile(e.target.files[0])}
            />
            <label
              htmlFor="file-input"
              className="cursor-pointer px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-medium rounded-lg transition-colors"
            >
              Select PDF
            </label>
          </>
        )}
      </div>
    </div>
  );
}
