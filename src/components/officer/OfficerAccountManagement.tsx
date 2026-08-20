import React, { useEffect, useState } from "react";
import { Users, UserCheck, Stethoscope, Landmark, Trash2, AlertTriangle, CheckCircle2, Search, RefreshCw } from "lucide-react";
import { userService, type ApiUserResponse } from "../../services/api";

export const OfficerAccountManagement: React.FC = () => {
  const [users, setUsers] = useState<ApiUserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeRoleTab, setActiveRoleTab] = useState<"farmer" | "veterinarian" | "officer">("farmer");
  const [searchQuery, setSearchQuery] = useState("");
  
  // Deactivation state
  const [deactivatingUser, setDeactivatingUser] = useState<ApiUserResponse | null>(null);
  const [deactivating, setDeactivating] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadUsers = () => {
    setLoading(true);
    setError(null);
    userService
      .getAllUsers()
      .then((data) => setUsers(data))
      .catch((err) => setError(err?.message || "Failed to fetch user accounts."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleConfirmDelete = async () => {
    if (!deactivatingUser) return;
    setDeactivating(true);
    setActionMessage(null);
    try {
      await userService.deleteUser(deactivatingUser.id);
      setActionMessage(`Account for ${deactivatingUser.fullName} (${deactivatingUser.officialId || deactivatingUser.id}) has been DEACTIVATED. All historical farm and incident data are preserved.`);
      setDeactivatingUser(null);
      loadUsers();
    } catch (err: any) {
      setError(err?.message || "Failed to deactivate account.");
    } finally {
      setDeactivating(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    if (u.role !== activeRoleTab) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const nameMatch = u.fullName.toLowerCase().includes(q);
    const emailMatch = u.email.toLowerCase().includes(q);
    const idMatch = (u.officialId || u.id).toLowerCase().includes(q);
    return nameMatch || emailMatch || idMatch;
  });

  const farmerCount = users.filter((u) => u.role === "farmer").length;
  const vetCount = users.filter((u) => u.role === "veterinarian").length;
  const officerCount = users.filter((u) => u.role === "officer").length;

  return (
    <div className="account-management-view" style={{ marginTop: "24px", background: "rgba(15, 23, 42, 0.6)", padding: "24px", borderRadius: "16px", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Users size={24} color="#10B981" />
            <h3 style={{ fontSize: "20px", fontWeight: "800", color: "#ffffff", margin: 0 }}>System Account Management</h3>
          </div>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: "4px 0 0" }}>
            View and manage persistent login accounts across the platform. Note: Deleting an account deactivates authentication access while strictly preserving historical farm data.
          </p>
        </div>

        <button
          onClick={loadUsers}
          className="btn-secondary-action"
          style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px" }}
        >
          <RefreshCw size={14} />
          Refresh List
        </button>
      </div>

      {actionMessage && (
        <div style={{ background: "rgba(16, 185, 129, 0.15)", border: "1px solid #10B981", borderRadius: "10px", padding: "12px 16px", color: "#34D399", fontSize: "13px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
          <CheckCircle2 size={18} />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Role Filter Tabs */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", paddingBottom: "12px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => setActiveRoleTab("farmer")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "8px",
            border: "0",
            background: activeRoleTab === "farmer" ? "#10B981" : "rgba(255, 255, 255, 0.05)",
            color: "#ffffff",
            fontWeight: "700",
            cursor: "pointer",
            fontSize: "13px",
          }}
        >
          <UserCheck size={16} />
          Farmers ({farmerCount})
        </button>

        <button
          type="button"
          onClick={() => setActiveRoleTab("veterinarian")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "8px",
            border: "0",
            background: activeRoleTab === "veterinarian" ? "#10B981" : "rgba(255, 255, 255, 0.05)",
            color: "#ffffff",
            fontWeight: "700",
            cursor: "pointer",
            fontSize: "13px",
          }}
        >
          <Stethoscope size={16} />
          Veterinarians ({vetCount})
        </button>

        <button
          type="button"
          onClick={() => setActiveRoleTab("officer")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "8px",
            border: "0",
            background: activeRoleTab === "officer" ? "#10B981" : "rgba(255, 255, 255, 0.05)",
            color: "#ffffff",
            fontWeight: "700",
            cursor: "pointer",
            fontSize: "13px",
          }}
        >
          <Landmark size={16} />
          Government Officers ({officerCount})
        </button>
      </div>

      {/* Search Input */}
      <div style={{ marginBottom: "16px" }}>
        <div className="input-with-icon" style={{ maxWidth: "360px" }}>
          <Search size={16} className="input-icon" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Search ${activeRoleTab}s by name, email, or ID...`}
            className="form-input"
            style={{ fontSize: "13px" }}
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="loading-state">Loading user accounts...</div>
      ) : error ? (
        <div className="form-error-banner">{error}</div>
      ) : filteredUsers.length === 0 ? (
        <div style={{ textAlign: "center", padding: "32px", color: "#94a3b8", background: "rgba(255,255,255,0.02)", borderRadius: "8px" }}>
          No accounts found matching criteria.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", color: "#ffffff", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "rgba(255, 255, 255, 0.05)", textTransform: "uppercase", fontSize: "11px", letterSpacing: "0.5px", color: "#94a3b8" }}>
                <th style={{ padding: "12px 16px", textAlign: "left" }}>Account ID</th>
                <th style={{ padding: "12px 16px", textAlign: "left" }}>Full Name</th>
                <th style={{ padding: "12px 16px", textAlign: "left" }}>Email &amp; Phone</th>
                <th style={{ padding: "12px 16px", textAlign: "left" }}>Account Status</th>
                <th style={{ padding: "12px 16px", textAlign: "center" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((u) => {
                const displayId = u.officialId || u.id;
                const isActive = u.isActive ?? true;
                return (
                  <tr key={u.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)", background: !isActive ? "rgba(239, 68, 68, 0.05)" : "transparent" }}>
                    <td style={{ padding: "12px 16px" }}>
                      <span style={{ fontWeight: "700", background: "rgba(255, 255, 255, 0.1)", padding: "2px 8px", borderRadius: "4px", fontSize: "12px" }}>
                        {displayId}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", fontWeight: "600" }}>{u.fullName}</td>
                    <td style={{ padding: "12px 16px", color: "#cbd5e1" }}>
                      <div>{u.email}</div>
                      {u.phone && <div style={{ fontSize: "11px", color: "#94a3b8" }}>{u.phone}</div>}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      {isActive ? (
                        <span style={{ color: "#10B981", background: "rgba(16, 185, 129, 0.15)", padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: "700" }}>
                          ● Active
                        </span>
                      ) : (
                        <span style={{ color: "#EF4444", background: "rgba(239, 68, 68, 0.15)", padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: "700" }}>
                          ● Deactivated
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "center" }}>
                      {isActive ? (
                        <button
                          onClick={() => setDeactivatingUser(u)}
                          style={{
                            background: "rgba(239, 68, 68, 0.15)",
                            border: "1px solid rgba(239, 68, 68, 0.3)",
                            color: "#EF4444",
                            padding: "6px 12px",
                            borderRadius: "6px",
                            fontSize: "12px",
                            fontWeight: "700",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <Trash2 size={14} />
                          Delete Account
                        </button>
                      ) : (
                        <span style={{ fontSize: "12px", color: "#94a3b8", italic: "true" }}>Disabled</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Confirmation Modal */}
      {deactivatingUser && (
        <div className="modal-backdrop" onClick={() => setDeactivatingUser(null)}>
          <div className="incident-modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "480px" }}>
            <div className="modal-header">
              <div className="header-title-box">
                <AlertTriangle size={24} color="#EF4444" />
                <div>
                  <span className="modal-eyebrow">CONFIRM ACCOUNT DEACTIVATION</span>
                  <h2 className="modal-title">Delete Account</h2>
                </div>
              </div>
            </div>

            <div style={{ padding: "16px 0" }}>
              <p style={{ color: "#ffffff", fontSize: "14px", margin: "0 0 12px" }}>
                Are you sure you want to delete the login account for <strong>{deactivatingUser.fullName}</strong> ({deactivatingUser.officialId || deactivatingUser.id})?
              </p>
              <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "8px", padding: "12px", fontSize: "12px", color: "#FCA5A5" }}>
                <strong>CRITICAL RULE ENFORCED:</strong> Deleting this account will ONLY disable the user's login access. It will <strong>NEVER</strong> delete farms, incidents, evidence, corrective actions, inspections, or historical data.
              </div>
            </div>

            <div className="form-actions-row">
              <button
                type="button"
                className="btn-secondary-action"
                onClick={() => setDeactivatingUser(null)}
                disabled={deactivating}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary-action"
                style={{ background: "#DC2626" }}
                onClick={handleConfirmDelete}
                disabled={deactivating}
              >
                {deactivating ? "Deactivating..." : "Confirm Delete Account"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
