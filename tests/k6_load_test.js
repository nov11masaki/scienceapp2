import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 30,            // 同時仮想ユーザー数
  duration: '2m',     // テスト時間
};

const BASE = __ENV.TARGET_URL || 'http://localhost:8080';

export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // 1) チャット送信（予想フェーズの簡易API）
  let chatPayload = JSON.stringify({ message: '体積は大きくなる' });
  let chatRes = http.post(`${BASE}/chat`, chatPayload, { headers: headers });
  check(chatRes, {
    'chat status 2xx': (r) => r.status >= 200 && r.status < 300,
  });
  sleep(Math.random() * 1 + 0.5);

  // 2) 要約トリガー（同期/非同期どちらでも挙動を確認）
  // 本番は非同期キューを推奨。ここでは /summary を呼ぶ例。
  let sumRes = http.get(`${BASE}/summary?class=5&number=1&unit=空気の温度と体積`);
  check(sumRes, {
    'summary status ok': (r) => r.status === 200 || r.status === 202 || r.status === 201 || r.status === 302,
  });

  sleep(1);
}
