/**
 * API Service for SMELens Mobile
 * 
 * Handles all communication with the SMELens backend.
 */

// Default to localhost for development
// Change this to your production URL when deploying
const API_BASE_URL = __DEV__ 
  ? 'http://192.168.1.100:8000'  // Replace with your local IP
  : 'https://api.smelens.com';

// For Android emulator, use 10.0.2.2 instead of localhost
// const API_BASE_URL = 'http://10.0.2.2:8000';

/**
 * Upload an image for OCR processing
 * 
 * @param {string} imageUri - Local URI of the image
 * @param {string} documentType - Type hint (receipt, invoice, handwritten, etc.)
 * @returns {Promise<Object>} - OCR result
 */
export async function uploadImage(imageUri, documentType = 'unknown') {
  const formData = new FormData();
  
  // Get filename from URI
  const filename = imageUri.split('/').pop();
  
  // Determine MIME type
  const match = /\.(\w+)$/.exec(filename);
  const type = match ? `image/${match[1]}` : 'image/jpeg';
  
  formData.append('file', {
    uri: imageUri,
    name: filename,
    type,
  });

  try {
    const response = await fetch(
      `${API_BASE_URL}/upload/?document_type=${documentType}`,
      {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
}

/**
 * Analyze an image without saving to database
 * 
 * @param {string} imageUri - Local URI of the image
 * @param {string} documentType - Type hint
 * @returns {Promise<Object>} - Full analysis result
 */
export async function analyzeImage(imageUri, documentType = 'unknown') {
  const formData = new FormData();
  
  const filename = imageUri.split('/').pop();
  const match = /\.(\w+)$/.exec(filename);
  const type = match ? `image/${match[1]}` : 'image/jpeg';
  
  formData.append('file', {
    uri: imageUri,
    name: filename,
    type,
  });

  try {
    const response = await fetch(
      `${API_BASE_URL}/upload/analyze?document_type=${documentType}`,
      {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Analysis failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Analysis error:', error);
    throw error;
  }
}

/**
 * Get upload history
 * 
 * @returns {Promise<Array>} - List of documents
 */
export async function getHistory() {
  try {
    const response = await fetch(`${API_BASE_URL}/upload/`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch history');
    }

    return await response.json();
  } catch (error) {
    console.error('History error:', error);
    throw error;
  }
}

/**
 * Get a specific document by ID
 * 
 * @param {number} docId - Document ID
 * @returns {Promise<Object>} - Document details
 */
export async function getDocument(docId) {
  try {
    const response = await fetch(`${API_BASE_URL}/upload/${docId}`);
    
    if (!response.ok) {
      throw new Error('Document not found');
    }

    return await response.json();
  } catch (error) {
    console.error('Get document error:', error);
    throw error;
  }
}

/**
 * Check API health
 * 
 * @returns {Promise<Object>} - Health status
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  } catch (error) {
    console.error('Health check error:', error);
    throw error;
  }
}

/**
 * Format currency amount
 * 
 * @param {number} amount - Amount value
 * @param {string} currency - Currency code
 * @returns {string} - Formatted amount
 */
export function formatCurrency(amount, currency = 'KES') {
  if (amount === null || amount === undefined) return '-';
  
  const symbols = {
    KES: 'KSh',
    USD: '$',
    EUR: '€',
    GBP: '£',
  };
  
  const symbol = symbols[currency] || currency;
  return `${symbol} ${amount.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Format date string
 * 
 * @param {string} dateStr - Date string
 * @returns {string} - Formatted date
 */
export function formatDate(dateStr) {
  if (!dateStr) return '-';
  
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export default {
  uploadImage,
  analyzeImage,
  getHistory,
  getDocument,
  checkHealth,
  formatCurrency,
  formatDate,
};
