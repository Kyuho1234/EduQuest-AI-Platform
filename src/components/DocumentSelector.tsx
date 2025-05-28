'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Select,
  VStack,
  Text,
  useToast,
} from '@chakra-ui/react';
import axios from 'axios';

interface Document {
  id: string;
  filename: string;
  upload_date: string;
}

interface DocumentSelectorProps {
  onDocumentSelect: (docId: string) => void;
}

export default function DocumentSelector({ onDocumentSelect }: DocumentSelectorProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('http://localhost:8000/api/documents');
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
      toast({
        title: '문서 목록 조회 실패',
        description: '문서 목록을 불러오는 중 오류가 발생했습니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = () => {
    if (selectedDocId) {
      onDocumentSelect(selectedDocId);
    }
  };

  return (
    <VStack spacing={4} align="stretch">
      <Text fontWeight="bold">기존 문서에서 문제 생성</Text>
      
      <Select
        placeholder="문서를 선택하세요"
        value={selectedDocId}
        onChange={(e) => setSelectedDocId(e.target.value)}
        isDisabled={isLoading}
      >
        {documents.map((doc) => (
          <option key={doc.id} value={doc.id}>
            {doc.filename} ({new Date(doc.upload_date).toLocaleDateString()})
          </option>
        ))}
      </Select>
      
      <Button
        onClick={handleSelect}
        colorScheme="green"
        isDisabled={!selectedDocId || isLoading}
        isLoading={isLoading}
        loadingText="로딩 중..."
      >
        선택한 문서로 문제 생성
      </Button>
    </VStack>
  );
}