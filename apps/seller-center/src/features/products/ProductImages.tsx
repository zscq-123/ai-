import { useEffect, useId, useRef, useState } from 'react'
import { mediaUrl, sellerApi } from '../../api'

type UploadJob = { id: string; file: File; preview: string; progress: number; error?: string }
const maxImages = 9
const maxFileSize = 5 * 1024 * 1024
const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']

export function ProductImages({ merchantId, imageUrls, disabled, onChange, onBusyChange }: {
  merchantId: string; imageUrls: string[]; disabled: boolean; onChange: (urls: string[]) => void; onBusyChange: (busy: boolean) => void
}) {
  const inputId = useId()
  const [jobs, setJobs] = useState<UploadJob[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const urls = useRef(imageUrls)
  const previews = useRef(new Set<string>())
  const draggedImage = useRef<number | null>(null)
  const uploadLock = useRef(false)
  const mounted = useRef(true)
  urls.current = imageUrls
  const change = (next: string[]) => { urls.current = next; onChange(next) }
  const busy = disabled || uploading

  useEffect(() => {
    mounted.current = true
    const activePreviews = previews.current
    return () => { mounted.current = false; activePreviews.forEach((url) => URL.revokeObjectURL(url)) }
  }, [])

  const removeJob = (job: UploadJob) => {
    URL.revokeObjectURL(job.preview); previews.current.delete(job.preview)
    setJobs((current) => current.filter((item) => item.id !== job.id))
  }
  const upload = async (batch: UploadJob[]) => {
    if (uploadLock.current) return
    uploadLock.current = true; setUploading(true); onBusyChange(true); setNotice('')
    let completed = 0
    try {
      for (const job of batch) {
        if (!mounted.current) break
        setJobs((current) => current.map((item) => item.id === job.id ? { ...item, error: undefined, progress: 0 } : item))
        try {
          const result = await sellerApi.uploadProductImage(merchantId, job.file, (progress) => {
            if (mounted.current) setJobs((current) => current.map((item) => item.id === job.id ? { ...item, progress } : item))
          })
          if (!mounted.current) break
          change([...urls.current, result.url]); removeJob(job); completed++
        } catch (reason) {
          if (mounted.current) setJobs((current) => current.map((item) => item.id === job.id ? { ...item, error: reason instanceof Error ? reason.message : '上传失败，请重试。' } : item))
        }
      }
    } finally {
      uploadLock.current = false
      if (mounted.current) { setUploading(false); onBusyChange(false); if (completed) setNotice(`已上传 ${completed} 张图片。保存商品后生效。`) }
    }
  }
  const addFiles = (files: File[]) => {
    if (busy || uploadLock.current) return
    setError(''); setDragging(false)
    const available = maxImages - urls.current.length - jobs.length
    if (files.length > available) { setError(`最多添加 ${maxImages} 张图片，当前还可添加 ${Math.max(0, available)} 张。`); return }
    const invalid = files.find((file) => !allowedTypes.includes(file.type) || file.size > maxFileSize || file.size === 0)
    if (invalid) { setError(`“${invalid.name}”不符合要求。请选择不超过 5 MB 的 JPG、PNG 或 WebP 图片。`); return }
    const next = files.map((file) => { const preview = URL.createObjectURL(file); previews.current.add(preview); return { id: crypto.randomUUID(), file, preview, progress: 0 } })
    if (!next.length) return
    setJobs((current) => [...current, ...next]); void upload(next)
  }
  const move = (from: number, to: number) => {
    if (busy || from === to || to < 0 || to >= imageUrls.length) return
    const next = [...imageUrls]; const [item] = next.splice(from, 1); next.splice(to, 0, item); change(next)
    setNotice(to === 0 ? '已设为封面，保存商品后生效。' : '图片顺序已调整，保存商品后生效。')
  }

  return <div className="product-image-editor">
    <div className="field-heading"><div><b>商品图片</b><span>首张图片作为封面，可拖动缩略图调整顺序。</span></div><span className="image-count">{imageUrls.length} / {maxImages}</span></div>
    <div className={`image-drop-area ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { if (event.dataTransfer.types.includes('Files')) { event.preventDefault(); if (!busy) setDragging(true) } }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false) }} onDrop={(event) => { event.preventDefault(); setDragging(false); if (event.dataTransfer.files.length) addFiles(Array.from(event.dataTransfer.files)) }}>
      <div className="image-grid">{imageUrls.map((url, index) => <div className="image-tile" key={`${url}-${index}`} draggable={!busy} onDragStart={(event) => { draggedImage.current = index; event.dataTransfer.setData('application/x-nova-image', String(index)); event.dataTransfer.effectAllowed = 'move' }} onDragEnd={() => { draggedImage.current = null }} onDragOver={(event) => { if (draggedImage.current !== null) event.preventDefault() }} onDrop={(event) => { if (draggedImage.current !== null) { event.preventDefault(); event.stopPropagation(); move(draggedImage.current, index); draggedImage.current = null } }}>
        <div className="image-picture"><img src={mediaUrl(url)} alt={`商品图片 ${index + 1}${index === 0 ? '，封面' : ''}`} draggable={false} />{index === 0 && <span className="cover-label">封面</span>}<button className="image-remove" type="button" aria-label={`删除第 ${index + 1} 张图片`} disabled={busy} onClick={() => { change(imageUrls.filter((_, imageIndex) => imageIndex !== index)); setNotice('图片已移除，保存商品后生效。') }}>×</button></div>
        <div className="image-controls"><button type="button" aria-label={`第 ${index + 1} 张图片前移`} disabled={busy || index === 0} onClick={() => move(index, index - 1)}>←</button><button type="button" disabled={busy || index === 0} onClick={() => move(index, 0)}>{index === 0 ? '主图' : '设为封面'}</button><button type="button" aria-label={`第 ${index + 1} 张图片后移`} disabled={busy || index === imageUrls.length - 1} onClick={() => move(index, index + 1)}>→</button></div>
      </div>)}{jobs.map((job) => <div className={`image-tile upload-tile ${job.error ? 'failed' : ''}`} key={job.id}><div className="image-picture"><img src={job.preview} alt={`${job.file.name} 上传预览`} /><div className="upload-overlay"><span>{job.error ? '上传失败' : `${job.progress}%`}</span>{!job.error && <progress value={job.progress} max={100} aria-label={`${job.file.name} 上传进度`} />}</div></div><div className="image-controls">{job.error ? <><button type="button" disabled={busy} onClick={() => void upload([job])}>重试</button><button type="button" disabled={busy} onClick={() => removeJob(job)}>移除</button></> : <span>{job.progress === 100 ? '正在处理' : '正在上传'}</span>}</div>{job.error && <p className="upload-item-error" role="alert">{job.error}</p>}</div>)}{imageUrls.length + jobs.length < maxImages && <label className={`upload-add ${busy ? 'disabled' : ''}`} htmlFor={inputId}><span aria-hidden="true">＋</span><b>{uploading ? '上传中…' : '添加图片'}</b><small>或拖放文件至此</small><input id={inputId} type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={busy} onChange={(event) => { addFiles(Array.from(event.target.files ?? [])); event.target.value = '' }} /></label>}</div>
    </div><p className="field-hint">支持 JPG、PNG、WebP，单张不超过 5 MB。最长边不超过 6000 像素，总像素不超过 1600 万。建议使用 1:1 清晰商品图。</p>
    {error && <p className="inline-error" role="alert">{error}</p>}<p className="upload-notice" role="status" aria-live="polite">{notice}</p>
  </div>
}
