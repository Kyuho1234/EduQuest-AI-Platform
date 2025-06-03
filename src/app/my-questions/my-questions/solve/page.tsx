import { Suspense } from 'react';
import SolveClientPage from './SolveClientPage';

export default function Page() {
  return (
    <Suspense fallback={<div>로딩 중...</div>}>
      <SolveClientPage />
    </Suspense>
  );
}
