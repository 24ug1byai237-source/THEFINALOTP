import React, { useEffect, useState } from "react";
import { X, Stethoscope, CheckCircle2, UserCheck, Phone, Mail, AlertCircle } from "lucide-react";
import { userService, type ApiUserResponse } from "../../services/api";

interface FarmerVetSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectVet?: (vet: ApiUserResponse) => void;
  currentSelectedVetId?: string | null;
}

export const FarmerVetSelectionModal: React.FC<FarmerVetSelectionModalProps> = ({
  isOpen,
  onClose,
  onSelectVet,
  currentSelectedVetId,
}) => {
  const [vets, setVets] = useState<ApiUserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVet, setSelectedVet] = useState<ApiUserResponse | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setError(null);
    userService
      .getVeterinarians()
      .then((data) => {
        setVets(data);
        if (currentSelectedVetId) {
          const match = data.find((v) => v.id === currentSelectedVetId || v.officialId === currentSelectedVetId);
          if (match) setSelectedVet(match);
        } else if (data.length > 0) {
          setSelectedVet(data[0]);
        }
      })
      .catch((err) => {
        setError(err?.message || "Failed to load active veterinarians from database.");
      })
      .finally(() => setLoading(false));
  }, [isOpen, currentSelectedVetId]);

  if (!isOpen) return null;

  const handleConfirmSelection = () => {
    if (!selectedVet) return;
    if (onSelectVet) {
      onSelectVet(selectedVet);
    }
    localStorage.setItem("assigned_vet_id", selectedVet.id);
    localStorage.setItem("assigned_vet_name", selectedVet.fullName);
    localStorage.setItem("assigned_vet_official_id", selectedVet.officialId || selectedVet.id);
    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      onClose();
    }, 1200);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="incident-modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
        <div className="modal-header">
          <div className="header-title-box">
            <Stethoscope size={24} className="icon-green" color="#10B981" />
            <div>
              <span className="modal-eyebrow">FARMER ↔ VETERINARIAN ASSIGNMENT</span>
              <h2 className="modal-title">Select Veterinarian</h2>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {saveSuccess ? (
          <div className="submitted-success-card" style={{ padding: "32px 20px" }}>
            <CheckCircle2 size={48} color="#10B981" style={{ margin: "0 auto 12px" }} />
            <h3 className="success-title">Veterinarian Assigned!</h3>
            <p className="success-desc">
              Connected to <strong>{selectedVet?.fullName}</strong> ({selectedVet?.officialId || selectedVet?.id}).
            </p>
          </div>
        ) : (
          <div className="incident-form-wrapper">
            <div className="incident-form-body">
              <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
                Select an active, verified Veterinarian registered in the system to handle your farm's incident verification and health advice.
              </p>

              {loading && <div className="loading-state">Fetching database accounts for active veterinarians...</div>}

              {error && (
                <div className="form-error-banner">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              {!loading && !error && vets.length === 0 && (
                <div style={{ textAlign: "center", padding: "24px", color: "#94a3b8" }}>
                  No active veterinarian accounts currently found in database.
                </div>
              )}

              {!loading && vets.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "320px", overflowY: "auto" }}>
                  {vets.map((vet) => {
                    const isSelected = selectedVet?.id === vet.id;
                    const displayId = vet.officialId || `VET-${vet.id.slice(0, 6).toUpperCase()}`;
                    return (
                      <div
                        key={vet.id}
                        onClick={() => setSelectedVet(vet)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "14px 16px",
                          borderRadius: "10px",
                          border: isSelected ? "2px solid #10B981" : "1px solid rgba(255, 255, 255, 0.1)",
                          background: isSelected ? "rgba(16, 185, 129, 0.08)" : "rgba(255, 255, 255, 0.03)",
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <div
                            style={{
                              width: "40px",
                              height: "40px",
                              borderRadius: "50%",
                              background: isSelected ? "#10B981" : "rgba(255, 255, 255, 0.1)",
                              display: "grid",
                              placeItems: "center",
                              color: "#ffffff",
                              fontWeight: "700",
                            }}
                          >
                            <Stethoscope size={20} />
                          </div>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ fontSize: "12px", fontWeight: "700", background: "rgba(16, 185, 129, 0.2)", color: "#34D399", padding: "2px 6px", borderRadius: "4px" }}>
                                {displayId}
                              </span>
                              <strong style={{ fontSize: "14px", color: "#ffffff" }}>{vet.fullName}</strong>
                            </div>
                            <div style={{ display: "flex", gap: "12px", fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                              <span><Mail size={12} style={{ display: "inline", marginRight: "4px" }} />{vet.email}</span>
                              {vet.phone && <span><Phone size={12} style={{ display: "inline", marginRight: "4px" }} />{vet.phone}</span>}
                            </div>
                          </div>
                        </div>
                        {isSelected && <UserCheck size={20} color="#10B981" />}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="form-actions-row">
              <button type="button" className="btn-secondary-action" onClick={onClose}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary-action"
                disabled={!selectedVet || loading}
                onClick={handleConfirmSelection}
              >
                Confirm Veterinarian
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
