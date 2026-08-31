const state = { integrity: 100, resolved: false };

const actionArea = document.querySelector('#action-area');
const result = document.querySelector('#result');
const integrityValue = document.querySelector('#integrity-value');
const integrityMeter = document.querySelector('#integrity-meter');
const sandboxDialog = document.querySelector('#sandbox-dialog');

function setIntegrity(value) {
  state.integrity = value;
  integrityValue.textContent = `${value}%`;
  integrityMeter.style.width = `${value}%`;
  integrityMeter.style.background = value < 60 ? 'var(--red)' : 'var(--green)';
}

function lockActions() {
  state.resolved = true;
  document.querySelectorAll('[data-action]').forEach((button) => { button.disabled = true; });
}

function showResult(kind, title, message, learning) {
  lockActions();
  result.className = `result ${kind}`;
  result.innerHTML = `
    <h2>${title}</h2>
    <p>${message}</p>
    <p><strong>复盘：</strong>${learning}</p>
    <button class="action restart" id="restart">重新开始</button>
  `;
  result.querySelector('#restart').addEventListener('click', resetGame);
}

function resolve(action) {
  if (state.resolved) return;

  if (action === 'accept') {
    setIntegrity(55);
    showResult(
      'accepted',
      '避难所通行凭证已泄露',
      '你打开了伪造的领取页面。陌生设备已尝试接入避难所网络，系统完整性 -45%。',
      '显示名称和邮件正文都可以被伪造。请比较完整发件人域名：<code>north-relief-logistics.co</code> 与可信供应商 <code>northrelief-logistics.co</code> 并不相同。'
    );
    return;
  }

  showResult(
    'secured',
    action === 'report' ? '威胁已举报' : '沙盒确认：恶意链接已隔离',
    action === 'report'
      ? '威胁情报已发送给附近避难所。你的系统保持安全。'
      : '隔离环境阻断了跳转与凭证请求。你安全地确认了这是一次域名仿冒。',
    '域名中的一个额外连字符就足以把你带往攻击者控制的站点。遇到紧急请求时，先检查完整域名，而不是只看品牌名称。'
  );
}

actionArea.addEventListener('click', (event) => {
  const action = event.target.dataset.action;
  if (!action || state.resolved) return;
  if (action === 'sandbox') {
    sandboxDialog.showModal();
    return;
  }
  resolve(action);
});

document.querySelector('#sandbox-report').addEventListener('click', () => {
  sandboxDialog.close();
  resolve('sandbox');
});

document.querySelector('#sandbox-close').addEventListener('click', () => sandboxDialog.close());

function resetGame() {
  state.resolved = false;
  setIntegrity(100);
  document.querySelectorAll('[data-action]').forEach((button) => { button.disabled = false; });
  result.className = 'result hidden';
  result.innerHTML = '';
}
