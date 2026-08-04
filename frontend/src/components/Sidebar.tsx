import type { AuthUser, BackendStatus, MenuItem, PageName } from "../types";

type SidebarProps = {
  activePage: PageName;
  menus: MenuItem[];
  backendStatus: BackendStatus;
  onSelect: (page: PageName) => void;
  currentUser: AuthUser;
  onLogout: () => void;
};

function MenuIcon({ page }: { page: PageName }) {
  if (page === "chat") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 5v14M5 12h14" />
      </svg>
    );
  }
  if (page === "documents" || page === "all-documents") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 4.5h10.5L19 8v11.5H5zM15 4.5V8h4M8 12h8M8 15.5h6" />
      </svg>
    );
  }
  if (page === "tasks") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8" />
        <path d="M12 8v4l3 2" />
      </svg>
    );
  }
  if (page === "rag-evaluation") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 19V10M12 19V5M19 19v-7M3 19.5h18" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 6.5h16M4 11.5h16M4 16.5h10" />
    </svg>
  );
}

export function Sidebar({
  activePage,
  menus,
  backendStatus,
  onSelect,
  currentUser,
  onLogout,
}: SidebarProps) {
  return (
    <aside className="app-sidebar">
      <div>
        <div className="app-sidebar-brand">
          <img
            className="app-brand-logo"
            src="/sheep-docusearch.png"
            alt="DocuSearch 小羊图标"
          />
          <h1>DocuSearch</h1>
        </div>

        <nav className="app-sidebar-nav">
          {menus.map((menu) => (
            <button
              key={menu.key}
              onClick={() => onSelect(menu.key)}
              className={
                activePage === menu.key
                  ? "app-sidebar-link is-active"
                  : "app-sidebar-link"
              }
            >
              <span className="app-sidebar-link-icon">
                <MenuIcon page={menu.key} />
              </span>
              {menu.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="app-sidebar-footer">
        <span
          className={
            backendStatus === "online"
              ? "app-status-dot is-online"
              : backendStatus === "offline"
                ? "app-status-dot is-offline"
                : "app-status-dot is-checking"
          }
        />
        <div>
          <p className="app-sidebar-footer-label">当前账号</p>
          <p className="app-sidebar-footer-value">{currentUser.username}</p>
        </div>
        <button className="app-logout-button" onClick={onLogout}>退出</button>
      </div>
    </aside>
  );
}
