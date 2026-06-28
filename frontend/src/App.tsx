import { Routes, Route, NavLink } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ProductsPage from './pages/ProductsPage';
import TypePage from './pages/TypePage';
import ComparePage from './pages/ComparePage';
import AdminLayout from './pages/AdminLayout';
import AdminLogin from './pages/AdminLogin';
import AdminHealth from './pages/AdminHealth';
import ShopAnalyzer from './pages/ShopAnalyzer';

export default function App() {
  return (
    <>
      <nav className="navbar">
        <div className="nav-inner">
          <NavLink to="/" className="nav-brand">Source Price</NavLink>
          <div className="nav-links">
            <NavLink to="/">首页</NavLink>
            <NavLink to="/products">订阅</NavLink>
            <NavLink to="/analyze">🔍 解析</NavLink>
          </div>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/product/:slug" element={<TypePage />} />
        <Route path="/compare/:slug" element={<ComparePage />} />
        <Route path="/analyze" element={<ShopAnalyzer />} />
        {/* Admin */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminHealth />} />
        </Route>
      </Routes>
    </>
  );
}
