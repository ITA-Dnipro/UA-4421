import { Link } from "react-router-dom";

export default function Navbar() {
  const isAuthenticated = !!localStorage.getItem("token");

  function handleLogout() {
    localStorage.removeItem("token");
    window.location.href = "/login";
  }

  return (
    <nav
      style={{
        display: "flex",
        gap: "20px",
        padding: "15px",
        background: "#f3f4f6",
        borderBottom: "1px solid #ddd"
      }}
    >
      {isAuthenticated && <Link to="/">Home</Link>}
      {isAuthenticated && <Link to="/dashboard">Dashboard</Link>}
      {isAuthenticated && <Link to="/messages">Messages</Link>}
      {isAuthenticated && <Link to="/startups/1">Startup</Link>}

      {!isAuthenticated && <Link to="/login">Login</Link>}
      {!isAuthenticated && <Link to="/register">Register</Link>}

      {isAuthenticated && (
        <button
          onClick={handleLogout}
          style={{
            marginLeft: "auto",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            fontWeight: "bold"
          }}
        >
          Logout
        </button>
      )}
    </nav>
  );
}
