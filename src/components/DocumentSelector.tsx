'use client';

import { Select, Button, VStack, Text } from '@chakra-ui/react';
import { useEffect, useState } from 'react';
import axios from 'axios';

interface Document {
  document_id: string;
  filename: string;
  created_at: string;
}

interface DocumentSelectorProps {
  userId: string;
  onSelect: (documentId: string, documentName: string) => void;
  refreshTrigger?: number;
}

export default function DocumentSelector({ userId, onSelect, refreshTrigger }: DocumentSelectorProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState('');

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const res = await axios.get(`http://localhost:8000/api/documents/${userId}`);
        setDocuments(res.data);
      } catch (error) {
        console.error('문서 목록 조회 실패', error);
      }
    };
    fetchDocuments();
  }, [userId, refreshTrigger]);

  const handleGenerate = () => {
    const selected = documents.find((d) => d.document_id === selectedId);
    if (selected && selectedId) onSelect(selectedId, selected.filename);
  };

  return (
    <VStack align="start" spacing={4}>
      <Text fontWeight="bold">문서 선택</Text>
      <Select placeholder="문서를 선택하세요" onChange={(e) => setSelectedId(e.target.value)}>
        {documents.map((doc) => (
          <option key={doc.document_id} value={doc.document_id}>
            {doc.filename} ({doc.created_at})
          </option>
        ))}
      </Select>
      <Button colorScheme="teal" onClick={handleGenerate} isDisabled={!selectedId}>
        선택한 문서로 문제 생성
      </Button>
    </VStack>
  );
}
