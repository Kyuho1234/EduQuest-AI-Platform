'use client';

import React, { useRef, useState } from 'react';
import {
  Box,
  Button,
  Text,
  VStack,
  useToast,
  Progress,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import axios from 'axios';

interface PDFUploaderProps {
  onUploadSuccess: (docId: string) => void;
}

export default function PDFUploader({ onUploadSuccess }: PDFUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const toast = useToast();

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      
      if (selectedFile.type !== 'application/pdf') {
        toast({
          title: '파일 형식 오류',
          description: 'PDF 파일만 업로드할 수 있습니다.',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setIsUploading(true);
      setUploadProgress(0);

      const response = await axios.post('http://localhost:8000/upload-pdf', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        },
      });

      toast({
        title: '업로드 성공!',
        description: 'PDF 파일이 성공적으로 업로드되었습니다.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      onUploadSuccess(response.data.doc_id);
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: '업로드 실패',
        description: '파일 업로드 중 오류가 발생했습니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <VStack spacing={4} align="stretch">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf"
        style={{ display: 'none' }}
      />
      
      <Button onClick={handleFileSelect} variant="outline">
        PDF 파일 선택
      </Button>
      
      {file && (
        <Alert status="info">
          <AlertIcon />
          선택된 파일: {file.name}
        </Alert>
      )}
      
      {isUploading && (
        <Box>
          <Text mb={2}>업로드 중... {uploadProgress}%</Text>
          <Progress value={uploadProgress} colorScheme="blue" />
        </Box>
      )}
      
      <Button
        onClick={handleUpload}
        colorScheme="blue"
        isDisabled={!file || isUploading}
        isLoading={isUploading}
        loadingText="업로드 중..."
      >
        업로드
      </Button>
    </VStack>
  );
}