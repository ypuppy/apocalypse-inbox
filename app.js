const state = {
  day: 1,
  integrity: 82,
  supplies: 46,
  intel: 18,
  unreadThreats: 1,
  resolved: false,
  night: false,
};

const elements = {
  tabs: [...document.querySelectorAll('[data-tab]')],
  panels: [...document.querySelectorAll('[data-panel]')],
  integrity: document.querySelector('#integrity-value'),
  supplies: document.querySelector('#supplies-value'),
  intel: document.querySelector('#intel-value'),
  threats: document.querySelector('#threat-value'),
  inboxBadge: document.querySelector('#inbox-badge'),
  result: document.querySelector('#result'),
  selection: document.querySelector('#base-selection'),
  impact: document.querySelector('#base-impact'),
  actionArea: document.querySelector('#action-area'),
  reportSummary: document.querySelector('#report-summary'),
  timeToggle: document.querySelector('#time-toggle'),
};

let baseScene;

function updateHud() {
  elements.integrity.textContent = `${state.integrity}%`;
  elements.supplies.textContent = state.supplies;
  elements.intel.textContent = state.intel;
  elements.threats.textContent = state.unreadThreats;
  elements.inboxBadge.textContent = state.unreadThreats;
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
}

function reportThreat(fromSandbox = false) {
  if (state.resolved) return;

  lockActions();
  state.unreadThreats = 0;
  state.intel += fromSandbox ? 8 : 6;
  updateHud();
  baseScene?.setBuildingState('radio', 'upgraded');
  elements.impact.textContent = '无线电站获得威胁情报：已升级域名过滤规则。';
  elements.reportSummary.innerHTML = '<strong>已提交：北境救援物流仿冒域名</strong><p>识别到额外连字符、二次跳转与凭证索取。无线电站获得了新的过滤规则。</p>';
  showTab('report');
  showResult('secured', '威胁已被阻断', `避难所获得 ${fromSandbox ? 8 : 6} 点情报；基地没有受到入侵。`, '显示名称可以可信，完整域名却可能被仿冒。紧急请求出现时，优先检查域名与可信联系渠道。');
}

function acceptThreat() {
  if (state.resolved) return;

  lockActions();
  state.integrity = Math.max(0, state.integrity - 45);
  state.unreadThreats = 0;
  updateHud();
  baseScene?.setBuildingState('relay', 'damaged');
  elements.impact.textContent = '网络中继器因凭证泄露而受损，夜晚的防线会更脆弱。';
  showTab('base');
  showResult('accepted', '避难所通行凭证已泄露', '伪造页面尝试接入避难所网络。系统完整性 -45%，网络中继器已在地图上标记为受损。', '品牌名称和邮件正文都能被伪造。可信供应商是 northrelief-logistics.co，而邮件中的 north-relief-logistics.co 多了一个连字符。');
}

elements.tabs.forEach((tab) => tab.addEventListener('click', () => showTab(tab.dataset.tab)));
elements.actionArea.addEventListener('click', (event) => {
  const action = event.target.dataset.action;
  if (!action || state.resolved) return;
  if (action === 'accept') acceptThreat();
  if (action === 'report') reportThreat(false);
  if (action === 'sandbox') showTab('sandbox');
});
document.querySelector('#sandbox-report').addEventListener('click', () => reportThreat(true));
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
    this.load.image('base-day', './assets/base-day.png');
  }

  create() {
    baseScene = this;
    this.add.image(480, 270, 'base-day').setDisplaySize(960, 540);

    this.createBuildingZone('command', 468, 175, 185, 120, '指挥室', '点击打开收件箱');
    this.createBuildingZone('radio', 132, 142, 118, 246, '无线电站', '接收外部求救');
    this.createBuildingZone('warehouse', 720, 172, 190, 160, '仓库', '储存补给');
    this.createBuildingZone('water', 708, 390, 165, 132, '净水站', '住民饮水');
    this.createBuildingZone('clinic', 535, 405, 145, 110, '医疗站', '处理伤员');
    this.createBuildingZone('relay', 142, 350, 120, 122, '网络中继器', '保护通讯链路');
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

updateHud();
