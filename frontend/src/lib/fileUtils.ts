/**
 * Generate SHA-256 hash for a file
 * @param file - The file to hash
 * @returns Promise resolving to the hex string hash
 */
export async function generateFileHash(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

/**
 * Upload a file directly to S3 using a presigned URL
 * @param presignedUrl - The presigned URL from the backend
 * @param file - The file to upload
 * @param contentType - The MIME type of the file
 * @param onProgress - Optional callback for upload progress
 */
export async function uploadToS3(
  presignedUrl: string,
  file: File,
  contentType: string,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    console.log('🔵 [S3 Upload] Starting upload to S3');
    console.log('📄 File:', file.name, 'Size:', file.size, 'Type:', file.type);
    console.log('🔑 Content-Type:', contentType);
    console.log('🔗 Presigned URL (first 100 chars):', presignedUrl.substring(0, 100) + '...');
    
    const xhr = new XMLHttpRequest();

    // Progress tracking
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = (e.loaded / e.total) * 100;
        console.log(`📊 Upload progress: ${percent.toFixed(2)}%`);
        onProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      console.log(`📡 S3 Response - Status: ${xhr.status}, StatusText: ${xhr.statusText}`);
      console.log('📋 Response Headers:', xhr.getAllResponseHeaders());
      
      if (xhr.status >= 200 && xhr.status < 300) {
        console.log('✅ S3 upload successful!');
        resolve();
      } else {
        console.error('❌ S3 upload failed with status:', xhr.status);
        console.error('Response text:', xhr.responseText);
        reject(new Error(`S3 upload failed with status ${xhr.status}: ${xhr.statusText}`));
      }
    });

    xhr.addEventListener("error", (e) => {
      console.error('❌ XHR error event:', e);
      console.error('XHR status:', xhr.status);
      console.error('XHR response:', xhr.responseText);
      reject(new Error("S3 upload failed - Network error"));
    });
    
    xhr.addEventListener("abort", () => {
      console.warn('⚠️  S3 upload aborted');
      reject(new Error("S3 upload aborted"));
    });

    console.log('🚀 Opening PUT request to S3...');
    xhr.open("PUT", presignedUrl);

    // IMPORTANT: This must match backend signed ContentType
    console.log('📝 Setting Content-Type header:', contentType);
    xhr.setRequestHeader("Content-Type", contentType);

    // ❌ REMOVE ACL (it breaks the signature)
    // xhr.setRequestHeader('x-amz-acl', 'private');

    console.log('📤 Sending file to S3...');
    xhr.send(file);
  });
}

/**
 * Format file size in human-readable format
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Validate file type and size
 * @param file - The file to validate
 * @param maxSizeMB - Maximum file size in MB (default: 10)
 * @returns Object with validation result and error message if any
 */
export function validateFile(
  file: File,
  maxSizeMB: number = 10
): { valid: boolean; error?: string } {
  // Validate file type
  const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  const fileExtension = file.name.toLowerCase();
  const isValidExtension = /\.(pdf|jpe?g|png|webp)$/i.test(fileExtension);

  if (!allowedTypes.includes(file.type) && !isValidExtension) {
    return {
      valid: false,
      error: 'Only PDF and image files (JPG, PNG, WEBP) are supported',
    };
  }

  // Validate file size
  const maxSize = maxSizeMB * 1024 * 1024;
  if (file.size > maxSize) {
    return {
      valid: false,
      error: `File size must be less than ${maxSizeMB}MB`,
    };
  }

  return { valid: true };
}
