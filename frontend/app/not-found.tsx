import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page">
      <div className="state-panel">
        <h1>404</h1>
        <p>요청한 페이지를 찾을 수 없습니다.</p>
        <Link className="button" href="/">홈으로 이동</Link>
      </div>
    </div>
  );
}
