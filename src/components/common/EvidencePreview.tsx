import React, { useEffect, useRef, useState } from "react";
import { ExternalLink, Image, FileText } from "lucide-react";
import { fetchMediaBlobUrl, isImageFile, isPdfFile, resolveMediaUrl } from "../../utils/mediaUrl";
import { useTranslation } from "../../context/LocaleContext";

interface EvidencePreviewProps {
  fileName: string;
  fileUrl: string;
  notes?: string;
  compact?: boolean;
}

export const EvidencePreview: React.FC<EvidencePreviewProps> = ({
  fileName,
  fileUrl,
  notes,
  compact = false,
}) => {
  const { t } = useTranslation();
  const mediaUrl = resolveMediaUrl(fileUrl);
  const showImage = mediaUrl && isImageFile(fileName || mediaUrl);
  const showPdf = mediaUrl && isPdfFile(fileName || mediaUrl);
  const [imageFailed, setImageFailed] = useState(false);
  const [shouldLoadImage, setShouldLoadImage] = useState(compact);
  const [blobUrl, setBlobUrl] = useState<string>("");
  const [opening, setOpening] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // The backend now requires an authenticated request to fetch media (it
  // used to be publicly readable by file id alone), so a plain <img src>
  // can't be pointed at the backend URL directly — fetch it as an
  // authenticated blob and render that instead.
  useEffect(() => {
    if (!showImage || !shouldLoadImage || !mediaUrl) return;
    let cancelled = false;
    let objectUrl = "";
    fetchMediaBlobUrl(mediaUrl)
      .then((url) => {
        if (cancelled) {
          if (url.startsWith("blob:")) URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setBlobUrl(url);
      })
      .catch(() => {
        if (!cancelled) setImageFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl.startsWith("blob:")) URL.revokeObjectURL(objectUrl);
    };
  }, [showImage, shouldLoadImage, mediaUrl]);

  useEffect(() => {
    if (compact || !showImage || shouldLoadImage) return;
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setShouldLoadImage(true);
          observer.disconnect();
        }
      },
      { rootMargin: "120px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [compact, showImage, shouldLoadImage]);

  const handleOpen = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (opening) return;
    setOpening(true);
    try {
      const url = blobUrl || (await fetchMediaBlobUrl(mediaUrl));
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      setImageFailed(true);
    } finally {
      setOpening(false);
    }
  };

  if (!mediaUrl) {
    return (
      <div className="evidence-file-card">
        <Image size={24} className="file-icon" />
        <div className="evidence-file-meta">
          <strong className="file-name">{fileName}</strong>
          <span className="text-muted">{t("vet.evidence.unavailable")}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`evidence-file-card evidence-file-card-rich ${compact ? "evidence-compact" : ""}`}
    >
      {showImage && !imageFailed ? (
        <a href={mediaUrl} onClick={handleOpen} className="evidence-thumb-link">
          {shouldLoadImage && blobUrl ? (
            <img
              src={blobUrl}
              alt={fileName}
              className="evidence-thumb-image"
              loading="lazy"
              decoding="async"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <div className="evidence-thumb-placeholder" aria-hidden>
              <Image size={24} className="file-icon" />
            </div>
          )}
        </a>
      ) : showPdf ? (
        <FileText size={32} className="file-icon" />
      ) : (
        <Image size={24} className="file-icon" />
      )}
      <div className="evidence-file-meta">
        <strong className="file-name">{fileName}</strong>
        {imageFailed && (
          <span className="text-muted evidence-load-fail">{t("vet.evidence.reloadHint")}</span>
        )}
        {notes && <p className="evidence-notes-preview">{notes}</p>}
        <a href={mediaUrl} onClick={handleOpen} className="evidence-open-link">
          <ExternalLink size={14} />
          {opening ? "…" : t("vet.evidence.open")}
        </a>
      </div>
    </div>
  );
};
