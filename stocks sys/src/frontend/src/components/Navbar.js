import React from 'react';
import { NavLink } from 'react-router-dom';
import '../styles/Navbar.css';

const Navbar = () => {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>StockAnalysis</h1>
      </div>
      <ul className="navbar-nav">
        <li className="nav-item">
          <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Dashboard
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/notifications" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Notifications
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/api-settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            API Settings
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/database-settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Database Settings
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/notification-settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Notification Settings
          </NavLink>
        </li>
      </ul>
    </nav>
  );
};

export default Navbar;