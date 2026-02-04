import { createContext, useContext, useState, useLayoutEffect, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext(undefined);


export const useAuth = () => {
  const authContext = useContext(AuthContext);
  
  if (!authContext) {
    throw new Error('useAuth must be used within the AuthProvider');
  }
  
  return authContext;
};



export const AuthProvider = ({ children }) => {
  
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true); // so the login screen isnt shown while the /refresh is being called
 
  // interceptors
  // useLayoutEffect is better cuz it runs before rendering components
  useLayoutEffect(() => {
  
    // 1- Request interceptor
    const authInterceptor = api.interceptors.request.use((config) => {
      
      // checks if there is a token and adds it to the header only
      // it doesn't check if it is a retry so it doesnt cause infinite loops
      config.headers.authorization =
        !config._retry && token ? `Bearer ${token}` : config.headers.Authorization;
      
      return config;
    });
    
    // 2- Response interceptor (catches erros)
    const refreshInterceptor = api.interceptors.response.use(
      (response) => response, // on success
      
      async (error) => {
        const originalRequest = error.config;
        
        // unauthorized and didnt do refresh yet
        if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url.includes('/refresh') ) {
          originalRequest._retry = true; // so it doesnt do an infinite loop
          
          try {
            
            const response = await api.post("/refresh");
            
            // 1- get the new access token
            const newAccessToken = response.data.access_token
            setToken(newAccessToken);
            
            // 2- retry the original request with the new token
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return api(originalRequest);
            
          } catch (refreshError) {
            // the refresh didnt work (cookie expired) so loggout
            setToken(null);
            return Promise.reject(refreshError);
          }
        }
        
        return Promise.reject(error)
        
      }
      
    );
    
    // just cleanup funcs (it removes interceptors when the component unmounts)
    return () => {
      api.interceptors.request.eject(authInterceptor);
      api.interceptors.response.eject(refreshInterceptor);
    };
    
    // DONT FORGET, THIS IS THE END OF useLayoutEffect
  }, [token]); // re runs if the token changes
  
  // 2- inital load check
  // when the page first loads, it tries to refresh immediately to see if use is logged in
  useEffect(() => {
    const persistLogin = async () => {
    
      try {
        const response = await api.post("/refresh");
        setToken(response.data.access_token);
        
      } catch (err) {
        console.error(`User not logged in, ${err}`);
      } finally {
        setLoading(false);
      }
    };
    
    
    if (!token) { persistLogin(); }
    
    else { setLoading(false); }
    
  }, []);
  
  // 3- login function
  const login = async (username, password) => {

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    // No need for a try/catch here cuz the UI to handles the error
    const response = await api.post('/login', formData);
    
    // Set the token (this triggers a re-render)
    setToken(response.data.access_token);
  };
  
  // 4- logout function
  const logout = async () => {
    try {
      await api.post('/logout');
    } catch (err) {
      console.error(err);
    } finally {
      setToken(null);
    }
  };
  
  return (
    <AuthContext.Provider value={{ token, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};