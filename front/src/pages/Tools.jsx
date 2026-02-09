import React, { useState, useEffect } from "react";

import Toast from "../components/Toast.jsx"
import FloatingMenu from '../components/FloatingMenu';

import api from "../api/axios.js";

// icons
const ExcelIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="40px" height="40px">
    <path fill="#4CAF50" d="M41,10H25v28h16c0.553,0,1-0.447,1-1V11C42,10.447,41.553,10,41,10z"/>
    <path fill="#FFF" d="M32 15H39V18H32zM32 25H39V28H32zM32 35H39V38H32zM24 43L4 43 4 5 24 5z"/>
    <path fill="#FFF" d="M21 11.5L17 18 13 11.5 11 11.5 16 19.5 11 27.5 13 27.5 17 21 21 27.5 23 27.5 18 19.5 23 11.5z"/>
  </svg>
);

const FileStackIcon = () => (
  <svg className="w-12 h-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
  
  
);

const Tools = () => {
  
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null); // toast message
  const [messageType, setMessageType] = useState(null); // to determine if toast is error or warn
  const [isMerging, setIsMerging] = useState(false);
  
  const [cooldownTimer, setCooldownTimer] = useState(0);
  
  
  useEffect(() => {
    if (cooldownTimer > 0) {
      const timerId = setTimeout(() => setCooldownTimer(c => c - 1), 1000);
      return () => clearTimeout(timerId);
    }
  }, [cooldownTimer]); // used to disable components
  
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    const existingNames = selectedFiles.map(f => f.name);
    
    // filter duplicates
    const newFiles = files.filter(file => {
      if (existingNames.includes(file.name)) {
        setErrorMessage(`Duplicate skipped: ${file.name}`);
        setMessageType("warn");
        return false;
      }
      
      // checks for excel extension
      if (!file.name.match(/\.(xlsx|xls)$/)) {
        setErrorMessage("Only Excel files (.xlsx) allowed!");
        setMessageType("error");
        return false;
      }
      return true;
      
    }).map(file => ({
      file,
      name: file.name,
      size: (file.size / 1024).toFixed(2) + " KB",
      id: Math.random().toString(36).substr(2, 9)
    }));
    
    // Add to list
    if (selectedFiles.length + newFiles.length > 10) {
      setErrorMessage("Max 10 files allowed");
      setMessageType("error");
      return;
    }
    
    setSelectedFiles(prev => [...prev, ...newFiles]);
  };
  
  const handleRemoveFile = (id) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== id));
  };
  
  const clearError = () => {
    setErrorMessage(null);
    setMessageType(null);
  }
  
  // MAIN FUNCTION
  // function to send request to merge given excel files
  const handleMerge = async () => {
    
    if (selectedFiles.length < 2) return;
    
    setIsMerging(true);
    setErrorMessage(null);
    setMessageType(null);
    
    const formData = new FormData();
    for (let i=0; i<selectedFiles.length; i++) {
      formData.append("files", selectedFiles[i].file);
    }
    
    try {
      const response = await api.post("/tools/merge", formData, {'responseType': 'blob'});
      
      const blob = response.data;
      let filename = "Merged_patients.xlsx"
      
      // get filename
      const contentDisposition = response.headers['content-disposition'];
      if (contentDisposition){
        const match = contentDisposition.match(/filename="?(.+)"?/);
        if (match){
          filename = match[1];
        }
      }
      
      // auto download
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click()
      
      // clean up
      link.remove()
      window.URL.revokeObjectURL(url);
      
      await new Promise(r => setTimeout(r, 2000));
      
      setCooldownTimer(5)
      
    } catch (errs) {
      let serverError = "An error occurred";
      
      if (errs.response?.data instanceof Blob && errs.response.data.type === "application/json"){
        const blobText = await errs.response.data.text();
        try {
          const errorJson = JSON.parse(blobText);
          serverError = errorJson.detail;
          
        } catch (e) {
          serverError = "Failed to parse error response";
        }
      }
      
      else {
        serverError = errs.response?.data?.detail || errs.message; // in case of network error
      }
      
      setErrorMessage(serverError);
      setMessageType("error");
      setCooldownTimer(5);
      
    } finally {
      setIsMerging(false)
    }
  };
  
  
  
  return (
    
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center py-12 px-4">
      
      
      {!isMerging &&
        <FloatingMenu />}
      
      {errorMessage &&
        <Toast
          message={errorMessage}
          type={messageType}
          onClose={clearError} />}
      
      <div className="bg-white shadow-xl rounded-2xl w-full max-w-lg overflow-hidden border border-gray-100">
        
        {/* Header */}
        <div className="bg-blue-900 p-6 text-white text-center relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-full opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
          <h1 className="text-2xl font-bold relative z-10">Report Merger</h1>
          <p className="text-blue-200 text-sm relative z-10 mt-1">Combine multiple patient lists into one master file.</p>
          <p className="text-blue-200 text-sm relative z-10 mt-1">More tools coming soon...</p>
        </div>
        
        <div className="p-8">
          
          {/* DRAG AND DROP */}
          <label className="border-2 border-dashed border-gray-300 rounded-xl bg-gray-50 hover:bg-blue-50 hover:border-blue-300 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center p-8 group">
            <input type="file" multiple accept=".xlsx, .xls" className="hidden" onChange={handleFileChange} />
            
            <div className="group-hover:scale-110 transition-transform duration-300">
              <FileStackIcon />
            </div>
            <p className="text-gray-500 font-medium group-hover:text-blue-600">Click to Browse or Drag Files</p>
            <p className="text-xs text-gray-400 mt-2">Supports .xlsx and .xls</p>
          </label>
          
          {/* FILE LIST AREA */}
          <div className="mt-6">
            <div className="flex justify-between items-center mb-2 px-1">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Queue</span>
              <span className="text-xs font-bold text-gray-400">{selectedFiles.length} / 10</span>
            </div>
            
            {/* List container */}
            <div className="space-y-3 min-h-[100px]">
              {selectedFiles.length === 0 ? (
                <div className="text-center py-8 text-gray-300 italic border border-transparent rounded-lg">
                  No files selected yet...
                </div>
              ) : (
                selectedFiles.map((file) => (
                  <div key={file.id} className="flex items-center bg-white border border-gray-200 p-3 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                    {/* Icon */}
                    <div className="shrink-0 mr-3">
                      <ExcelIcon />
                    </div>
                    {/* Info */}
                    <div className="grow min-w-0">
                      <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
                      <p className="text-xs text-gray-400">{file.size}</p>
                    </div>
                    {/* Delete button */}
                    <button
                      onClick={() => handleRemoveFile(file.id)}
                      className="ml-2 text-gray-400 hover:text-red-500 p-1 rounded-full hover:bg-red-50 transition-colors cursor-pointer"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
          
          {/* MERGE BUTTON */}
          <button
            type="button"
            onClick={handleMerge}
            className="w-full text-center cursor-pointer bg-blue-900 mt-5 hover:bg-[#0d2559] transition-colors duration-500 shadow-[0px_4px_32px_0_rgba(99,102,241,.70)] px-6 py-3 rounded-xl border border-slate-500 text-white font-medium group disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none"
            disabled={selectedFiles.length < 2 || selectedFiles.length === 0 || isMerging}
          >
            <div className="relative overflow-hidden">
              <p className="text-center group-hover:-translate-y-7 duration-[1.125s] ease-[cubic-bezier(0.19,1,0.22,1)]">
                {isMerging ? "Merging..." : "Ready?"}
              </p>
              <p className="w-full text-center absolute top-7 left-0 group-hover:top-0 duration-[1.125s] ease-[cubic-bezier(0.19,1,0.22,1)]">
                  {isMerging ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing...
                    </>
                  ) : (
                    `Merge ${selectedFiles.length > 0 ? selectedFiles.length : ""} Files`
                  )}
              </p>
            </div>
          </button>
        
        </div>
      </div>
      
    </div>
  );
};

export default Tools;