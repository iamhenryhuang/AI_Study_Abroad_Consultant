import { useState, useRef } from 'react'
import { UploadCloud, FileText, CheckCircle2, Trash2 } from 'lucide-react'

export function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected && selected.type === 'application/pdf') {
      setFile(selected)
    } else if (selected) {
      alert('請上傳 PDF 格式的檔案')
    }
    if (e.target) {
      e.target.value = ''
    }
  }

  return (
    <div className="mb-6">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 mb-3">Context</p>

      <div
        className={`relative rounded-xl border transition-all duration-300 overflow-hidden mx-1 ${file
            ? 'border-indigo-500/30 bg-indigo-500/10 shadow-[0_0_15px_rgba(99,102,241,0.1)]'
            : 'border-dashed border-gray-700 bg-transparent hover:border-indigo-400 hover:bg-[#2d2d34]/60 cursor-pointer'
          }`}
        onClick={() => {
          if (!file) fileInputRef.current?.click()
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,application/pdf"
          className="hidden"
        />

        {file ? (
          <div className="flex items-center gap-3 p-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/20 flex flex-col items-center justify-center text-indigo-400 shrink-0">
              <FileText size={18} />
            </div>
            <div className="flex-1 min-w-0 pr-1">
              <p className="text-sm font-medium text-gray-200 truncate">{file.name}</p>
              <p className="text-[10px] text-indigo-300 flex items-center gap-1 mt-0.5">
                <CheckCircle2 size={10} className="text-emerald-400" />
                解析完成，隨時待命
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setFile(null)
              }}
              title="移除履歷"
              className="p-1.5 mr-1 text-gray-400 hover:text-red-400 hover:bg-white/10 rounded-md transition-colors"
            >
              <Trash2 size={15} />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-4 gap-1.5 text-center text-gray-400 hover:text-gray-300">
            <div className="p-2 bg-gray-800/50 rounded-full mb-1">
              <UploadCloud size={20} className="text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-300">上傳履歷 (PDF)</p>
            <p className="text-[10px] text-gray-500 leading-tight">讓 AI 提供精準<br />個人落點分析</p>
          </div>
        )}
      </div>
    </div>
  )
}
