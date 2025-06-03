'use client';

import { useEffect, useRef, useState } from 'react';
import {
  Box,
  Heading,
  VStack,
  HStack,
  Text,
  Spinner,
  Divider,
  Center,
  Button,
  Checkbox,
  useToast,
  Spacer,
} from '@chakra-ui/react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

interface DocumentItem {
  document_id: string;
  filename: string;
  created_at: string;
}

export default function DocumentListPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleteMode, setDeleteMode] = useState(false); // 삭제모드 여부

  /* ───────────────────── 로그인 체크 ───────────────────── */
  useEffect(() => {
    if (status === 'unauthenticated') router.replace('/auth/signin');
  }, [status, router]);

  /* ───────────────────── 문서 목록 조회 ───────────────────── */
  const fetchDocuments = async () => {
    if (!session?.user?.id) return;
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${session.user.id}`);
      const data = await res.json();
      setDocuments(data);
    } catch (e) {
      console.error('문서 조회 실패:', e);
    } finally {
      setLoading(false);
      setSelected(new Set());
      setDeleteMode(false); // 삭제모드 초기화
    }
  };

  useEffect(() => {
    if (status === 'authenticated') fetchDocuments();
  }, [status, session?.user?.id]);

  /* ───────────────────── 업로드 ───────────────────── */
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
      toast({ title: 'PDF 파일만 업로드 가능합니다.', status: 'error' });
      return;
    }

    if (!session?.user?.id) {
      toast({ title: '로그인이 필요합니다.', status: 'error' });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', session.user.id);

    setUploading(true);
    try {
      await axios.post('http://localhost:8000/api/upload-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast({ title: '업로드 성공', status: 'success' });
      fetchDocuments();
    } catch {
      toast({ title: '업로드 실패', status: 'error' });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  /* ───────────────────── 체크 및 삭제 ───────────────────── */
  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleDeleteSelected = async () => {
    if (selected.size === 0) return;
    if (!confirm('선택한 문서를 삭제하시겠습니까?')) return;

    try {
      await Promise.all(
        Array.from(selected).map((id) =>
          axios.delete(`http://localhost:8000/api/documents/${id}`),
        ),
      );
      toast({ title: '삭제 완료', status: 'info' });
      fetchDocuments();
    } catch {
      toast({ title: '삭제 실패', status: 'error' });
    }
  };

  /* ───────────────────── 로딩 상태 ───────────────────── */
  if (status === 'loading' || !session) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  /* ───────────────────── 렌더링 ───────────────────── */
  return (
    <Box maxW="container.md" mx="auto" py={10}>
      <Heading mb={4}>📄 학습자료 목록</Heading>

      {/* 문서 목록 */}
      {loading ? (
        <Spinner />
      ) : documents.length === 0 ? (
        <Text>등록된 문서가 없습니다.</Text>
      ) : (
        <VStack spacing={0} align="stretch" divider={<Divider />}>
          {documents.map((doc) => (
            <Box key={doc.document_id} p={4}>
              <HStack justify="space-between" align="center">
                {deleteMode ? (
                  <Checkbox
                    isChecked={selected.has(doc.document_id)}
                    onChange={() => toggleSelect(doc.document_id)}
                    mr={4} // 체크박스와 문서 간 간격
                  />
                ) : null}

                <Box flex="1">
                  <Text fontWeight="bold">{doc.filename}</Text>
                  <Text fontSize="sm" color="gray.500">
                    {doc.created_at}
                  </Text>
                </Box>
              </HStack>
            </Box>
          ))}
        </VStack>
      )}

      {/* 상단 버튼 영역 */}
      <HStack justify="flex-end" mb={4}>
        <Box>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            onChange={handleUpload}
            style={{ display: 'none' }}
            id="pdf-upload"
          />
          <label htmlFor="pdf-upload">
            <Button as="span" colorScheme="teal" isLoading={uploading}>
              추가
            </Button>
          </label>
        </Box>

        {deleteMode ? (
          <>
            <Button
              colorScheme="red"
              onClick={handleDeleteSelected}
              isDisabled={selected.size === 0}
            >
              삭제
            </Button>
            <Button onClick={() => setDeleteMode(false)}>취소</Button>
          </>
        ) : (
          <Button colorScheme="teal" onClick={() => setDeleteMode(true)}>
            삭제
          </Button>
        )}
      </HStack>

    </Box>
  );
}
