import axios from 'axios';
import { toast } from 'react-toastify';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add the auth token to headers
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An unknown error occurred';
    
    // You can expand this to handle specific status codes
    if (error.response?.status === 401) {
      // For example, redirect to login or refresh token
      localStorage.removeItem('token');
      // Optionally, redirect to login page
      // window.location.href = '/login';
      toast.error('Authentication failed. Please log in again.');
    } else {
      toast.error(message);
    }

    return Promise.reject(error);
  }
);

export default api;
