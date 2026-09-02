const state = {
  day: 1,
  integrity: 82,
  supplies: 46,
  coins: 30,
  intel: 18,
  seeds: 0,
  sandboxUses: 1,
  unreadThreats: 1,
  resolved: false,
  night: false,
  flags: new Set(),
  guaranteedNightEffects: [],
  deferredEvents: [],
  construction: { blueprints: new Set(), components: {}, labour: 0, materials: { wood: 0, scrap: 0 } },
};

const elements = {
  tabs: [...document.querySelectorAll('[data-tab]')],
  panels: [...document.querySelectorAll('[data-panel]')],
  integrity: document.querySelector('#integrity-value'),
  supplies: document.querySelector('#supplies-value'),
  coins: document.querySelector('#coins-value'),
  intel: document.querySelector('#intel-value'),
  sandbox: document.querySelector('#sandbox-value'),
  threats: document.querySelector('#threat-value'),
  inboxBadge: document.querySelector('#inbox-badge'),
  result: document.querySelector('#result'),
  selection: document.querySelector('#base-selection'),
  impact: document.querySelector('#base-impact'),
  actionArea: document.querySelector('#action-area'),
  reportSummary: document.querySelector('#report-summary'),
  timeToggle: document.querySelector('#time-toggle'),
  mailCount: document.querySelector('#mail-count'),
  mailFamily: document.querySelector('#mail-family'),
  mailSubject: document.querySelector('#mail-subject'),
  mailSender: document.querySelector('#mail-sender'),
  mailTime: document.querySelector('#mail-time'),
  mailBody: document.querySelector('#mail-body'),
  mailClue: document.querySelector('#mail-clue'),
  sandboxLog: document.querySelector('#sandbox-log'),
  verifyClue: document.querySelector('#verify-clue'),
  sandboxAction: document.querySelector('[data-action="sandbox"]'),
};

let baseScene;
let activeCard = eventCards.find((card) => card.id === 'shipment-water-filter-redirect');

const familyLabels = {
  'system-transport': '系统运输',
  'world-market': '世界交易',
  people: '人员与求救',
  maintenance: '系统维护',
};

function updateHud() {
  elements.integrity.textContent = `${state.integrity}%`;
  elements.supplies.textContent = state.supplies;
  elements.coins.textContent = state.coins;
  elements.intel.textContent = state.intel;
  elements.sandbox.textContent = `${state.sandboxUses}/1`;
  elements.threats.textContent = state.unreadThreats;
  elements.inboxBadge.textContent = state.unreadThreats;
  elements.mailCount.textContent = `收件箱 / ${state.unreadThreats} 封未读`;
}

function showTab(name) {
  elements.tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
  elements.panels.forEach((panel) => panel.classList.toggle('hidden', panel.dataset.panel !== name));
}

function showResult(kind, title, message, learning) {
  elements.result.className = `result ${kind}`;
  elements.result.innerHTML = `
    <h2>${title}</h2>
    <p>${message}</p>
    <p><strong>复盘：</strong>${learning}</p>
    <button class="secondary-button" id="result-base" type="button">查看基地影响</button>
  `;
  elements.result.querySelector('#result-base').addEventListener('click', () => showTab('base'));
}

function lockActions() {
  state.resolved = true;
  document.querySelectorAll('[data-action]').forEach((button) => { button.disabled = true; });
  document.querySelector('#sandbox-report').disabled = true;
  elements.verifyClue.disabled = true;
}

function renderCard(card) {
  elements.mailFamily.textContent = familyLabels[card.family];
  elements.mailSubject.textContent = card.subject;
  elements.mailSender.textContent = card.sender;
  elements.mailTime.textContent = card.time;
  elements.mailClue.textContent = '';
  elements.mailClue.classList.add('hidden');
  elements.verifyClue.disabled = false;
  elements.verifyClue.textContent = `花 ${card.verificationCost ?? 2} 金币核验`;
  document.querySelector('#sandbox-report').disabled = true;
  elements.sandboxAction.disabled = card.sandboxEligible === false || state.sandboxUses <= 0;
  elements.sandboxAction.textContent = card.sandboxEligible === false
    ? '此邮件不能使用沙盒'
    : `隔离进沙盒（${state.sandboxUses}/1）`;
  document.querySelector('[data-action="accept"]').textContent = card.acceptLabel ?? '接受并执行';
  elements.mailBody.replaceChildren();
  card.paragraphs.forEach((text) => {
    const paragraph = document.createElement('p');
    paragraph.textContent = text;
    if (text.includes('：') && (text.includes('/') || text.includes('页面'))) paragraph.classList.add('fake-link');
    elements.mailBody.append(paragraph);
  });
  elements.sandboxLog.replaceChildren();
  card.sandbox.forEach((text, index) => {
    const line = document.createElement('p');
    line.textContent = `${index === card.sandbox.length - 1 && card.truth === 'malicious' ? '! ' : '> '}${text}`;
    if (index === card.sandbox.length - 1 && card.truth === 'malicious') line.classList.add('danger');
    elements.sandboxLog.append(line);
  });
  const conclusion = document.createElement('p');
  conclusion.classList.add('safe');
  conclusion.textContent = card.truth === 'malicious' ? '✓ 隔离环境没有执行异常操作。' : '✓ 未发现异常行为；仍请与订单档案交叉核验。';
  elements.sandboxLog.append(conclusion);
}

function revealVerification() {
  if (state.resolved || !activeCard.clue || !elements.mailClue.classList.contains('hidden')) return;
  const cost = activeCard.verificationCost ?? 2;
  if (state.coins < cost) {
    elements.impact.textContent = '金币不足，无法调用外部核验档案。';
    return;
  }
  state.coins -= cost;
  elements.mailClue.textContent = activeCard.clue;
  elements.mailClue.classList.remove('hidden');
  elements.verifyClue.disabled = true;
  elements.verifyClue.textContent = '核验完成';
  updateHud();
}

function useSandbox() {
  if (state.resolved) return;
  if (activeCard.sandboxEligible === false) {
    elements.impact.textContent = '此事件没有可隔离的链接或附件；请改用付费核验。';
    return;
  }
  if (state.sandboxUses <= 0) {
    elements.impact.textContent = '今天的沙盒额度已用尽，明天清晨才会恢复。';
    return;
  }
  state.sandboxUses -= 1;
  document.querySelector('#sandbox-report').disabled = false;
  elements.sandboxAction.disabled = true;
  elements.sandboxAction.textContent = '今日沙盒已使用';
  updateHud();
  showTab('sandbox');
}

function applyResources(resources = {}) {
  Object.entries(resources).forEach(([resource, amount]) => {
    state[resource] = Math.max(0, (state[resource] ?? 0) + amount);
  });
}

function applyConstructionReward(reward) {
  if (!reward) return;
  reward.blueprints?.forEach((blueprint) => state.construction.blueprints.add(blueprint));
  Object.entries(reward.components ?? {}).forEach(([component, amount]) => {
    state.construction.components[component] = (state.construction.components[component] ?? 0) + amount;
  });
  state.construction.labour += reward.labour ?? 0;
  Object.entries(reward.materials ?? {}).forEach(([material, amount]) => {
    state.construction.materials[material] = (state.construction.materials[material] ?? 0) + amount;
  });
}

function resolveMail(action) {
  if (state.resolved) return;
  const outcome = activeCard.outcomes[action];
  if (!outcome) return;

  lockActions();
  state.unreadThreats = 0;
  applyResources(outcome.resources);
  applyConstructionReward(outcome.constructionReward);
  if (outcome.guaranteedNightEffect) state.guaranteedNightEffects.push(outcome.guaranteedNightEffect);
  if (outcome.retryAfterDays || outcome.marketBlacklistDays || outcome.followUp) state.deferredEvents.push({ cardId: activeCard.id, ...outcome });
  if (outcome.facility) baseScene?.setBuildingState(outcome.facility, outcome.facilityState);
  if (outcome.unlockExpansion) baseScene?.unlockExpansion(outcome.unlockExpansion);
  elements.impact.textContent = outcome.impact;
  updateHud();

  if (outcome.report) {
    elements.reportSummary.innerHTML = `<strong>已提交：${activeCard.subject}</strong><p>${outcome.report}</p>`;
    showTab('report');
  } else {
    showTab('base');
  }
  showResult(outcome.kind, outcome.title, outcome.message, outcome.learning);
}

elements.tabs.forEach((tab) => tab.addEventListener('click', () => showTab(tab.dataset.tab)));
elements.actionArea.addEventListener('click', (event) => {
  const action = event.target.dataset.action;
  if (!action || state.resolved) return;
  if (action === 'accept' || action === 'report') resolveMail(action);
  if (action === 'sandbox') useSandbox();
});
elements.verifyClue.addEventListener('click', revealVerification);
document.querySelector('#sandbox-report').addEventListener('click', () => resolveMail('report'));
document.querySelector('#return-base').addEventListener('click', () => showTab('base'));
elements.timeToggle.addEventListener('click', () => {
  state.night = !state.night;
  elements.timeToggle.textContent = state.night ? '切换至白天' : '切换至夜晚';
  baseScene?.setNight(state.night);
});
document.addEventListener('open-inbox', () => showTab('inbox'));

class ShelterScene extends Phaser.Scene {
  constructor() {
    super('ShelterScene');
    this.buildings = new Map();
  }

  preload() {
    this.load.image('base-day', './assets/base-day.webp');
  }

  create() {
    baseScene = this;
    this.add.image(480, 270, 'base-day').setDisplaySize(960, 540);

    this.createBuildingZone('command', 468, 175, 185, 120, '指挥室', '点击打开收件箱');
    this.createBuildingZone('radio', 132, 142, 118, 246, '无线电站', '接收外部求救');
    this.createBuildingZone('warehouse', 720, 172, 190, 160, '仓库', '储存补给');
    this.createBuildingZone('clinic', 535, 405, 145, 110, '医疗站', '处理伤员');
    this.createBuildingZone('relay', 142, 350, 120, 122, '网络中继器', '保护通讯链路');
    this.createExpansionZone('garden', 245, 246, 168, 124, '菜园用地', '未开发 · 需要菜园蓝图与种子');
    this.createExpansionZone('water', 724, 385, 170, 134, '净水设施用地', '未开发 · 需要净水器与滤芯');
    this.createExpansionZone('west-yard', 285, 365, 135, 146, '西侧扩建地块', '预留 · 等待后续任务解锁');
    this.createExpansionZone('east-yard', 842, 360, 118, 162, '东侧扩建地块', '预留 · 等待后续任务解锁');
    this.createExpansionZone('south-yard', 445, 483, 212, 74, '南门外扩区', '预留 · 可扩展防线或工坊');
    this.createResidents();

    this.nightOverlay = this.add.rectangle(480, 270, 960, 540, 0x071021, 0).setDepth(20);
    this.glowLayer = this.add.graphics().setDepth(21);
    this.setNight(false);
  }

  createBuildingZone(id, x, y, width, height, label, description) {
    const frame = this.add.rectangle(x, y, width, height, 0xffdf7d, 0).setStrokeStyle(3, 0xffdf7d, 0).setDepth(12);
    const marker = this.add.circle(x + width / 2 - 14, y - height / 2 + 14, 7, 0xffdf7d, 0).setDepth(13);
    const zone = this.add.zone(x, y, width, height).setInteractive({ useHandCursor: true }).setDepth(14);

    zone.on('pointerover', () => {
      frame.setStrokeStyle(3, 0xffdf7d, .92);
      marker.setFillStyle(0xffdf7d).setAlpha(1);
      elements.selection.textContent = `${label} · ${description}`;
    });
    zone.on('pointerout', () => {
      if (!this.buildings.get(id)?.status) {
        frame.setStrokeStyle(3, 0xffdf7d, 0);
        marker.setAlpha(0);
      }
    });
    zone.on('pointerdown', () => {
      elements.selection.textContent = `${label} · ${description}`;
      if (id === 'command') document.dispatchEvent(new CustomEvent('open-inbox'));
    });

    this.buildings.set(id, { frame, marker, label, description, status: null });
  }

  createExpansionZone(id, x, y, width, height, label, description) {
    const frame = this.add.rectangle(x, y, width, height, 0x8acb81, 0).setStrokeStyle(2, 0x8acb81, 0).setDepth(12);
    const marker = this.add.circle(x + width / 2 - 13, y - height / 2 + 13, 6, 0x8acb81, 0).setDepth(13);
    const zone = this.add.zone(x, y, width, height).setInteractive({ useHandCursor: true }).setDepth(14);

    zone.on('pointerover', () => {
      frame.setStrokeStyle(2, 0x8acb81, .88);
      marker.setFillStyle(0x8acb81).setAlpha(1);
      const status = this.buildings.get(id)?.status;
      elements.selection.textContent = status === 'locked'
        ? `${label} · ${description}`
        : `${label} · 蓝图已到位，可部署设施`;
    });
    zone.on('pointerout', () => {
      if (this.buildings.get(id)?.status === 'locked') {
        frame.setStrokeStyle(2, 0x8acb81, 0);
        marker.setAlpha(0);
      }
    });
    zone.on('pointerdown', () => {
      const status = this.buildings.get(id)?.status;
      if (status === 'locked') {
        elements.selection.textContent = `${label} · 未解锁`;
        elements.impact.textContent = '这块地已预留。后续正确处置邮件可带来蓝图、物资或施工权限。';
      } else {
        elements.selection.textContent = `${label} · 蓝图已到位，可部署设施`;
      }
    });

    this.buildings.set(id, { frame, marker, label, description, status: 'locked', kind: 'expansion' });
  }

  createResidents() {
    [[345, 290, 0xf1c278], [590, 290, 0xe57e72], [635, 340, 0x90c8d0]].forEach(([x, y, color], index) => {
      const resident = this.add.container(x, y).setDepth(11);
      resident.add([
        this.add.ellipse(0, 9, 16, 7, 0x18311f, .35),
        this.add.rectangle(0, 0, 8, 13, color, 1),
        this.add.rectangle(0, -10, 8, 8, 0xf2c99b, 1),
      ]);
      this.tweens.add({
        targets: resident,
        x: x + (index % 2 ? 34 : -30),
        duration: 2800 + index * 400,
        yoyo: true,
        repeat: -1,
        ease: 'Sine.easeInOut',
      });
    });
  }

  setBuildingState(id, status) {
    const building = this.buildings.get(id);
    if (!building) return;

    building.status = status;
    if (status === 'damaged') {
      building.frame.setStrokeStyle(4, 0xff7168, 1);
      building.marker.setFillStyle(0xff7168).setAlpha(1);
      elements.selection.textContent = `${building.label} · 受损，需要物资修复`;
    }
    if (status === 'upgraded') {
      building.frame.setStrokeStyle(4, 0xa7d97d, 1);
      building.marker.setFillStyle(0xa7d97d).setAlpha(1);
      elements.selection.textContent = `${building.label} · 已升级域名过滤规则`;
    }
    if (status === 'available') {
      building.frame.setStrokeStyle(3, 0x8acb81, 1);
      building.marker.setFillStyle(0x8acb81).setAlpha(1);
      elements.selection.textContent = `${building.label} · 蓝图已到位，可部署设施`;
    }
  }

  unlockExpansion(id) {
    this.setBuildingState(id, 'available');
  }

  setNight(isNight) {
    this.nightOverlay.setAlpha(isNight ? .61 : 0);
    this.glowLayer.clear();
    if (isNight) {
      this.glowLayer.fillStyle(0xffdc7e, .16);
      [[468, 175], [132, 142], [720, 172], [708, 390], [535, 405], [142, 350]].forEach(([x, y]) => this.glowLayer.fillCircle(x, y, 74));
      elements.impact.textContent = '夜晚降临：受损的网络中继器会使外围防线更加脆弱。';
    } else if (!state.resolved) {
      elements.impact.textContent = '白天稳定：无线电站正在接收补给请求。';
    }
  }
}

new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game-container',
  width: 960,
  height: 540,
  backgroundColor: '#6fa85c',
  pixelArt: true,
  antialias: false,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: ShelterScene,
});

renderCard(activeCard);
updateHud();
