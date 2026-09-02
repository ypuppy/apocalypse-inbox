const state = {
  day: 1,
  integrity: 82,
  supplies: 46,
  coins: 30,
  intel: 18,
  seeds: 0,
  sandboxUses: 1,
  unread: 1,
  resolved: false,
  night: false,
  screen: 'base',
  baseHint: '指挥室有一封待处理邮件。',
  impact: '无线电站正在接收外部请求。',
  report: null,
  result: null,
  guaranteedNightEffects: [],
  deferredEvents: [],
  construction: { blueprints: new Set(), components: {}, labour: 0, materials: { wood: 0, scrap: 0 } },
};

const activeCard = eventCards.find((card) => card.id === 'shipment-water-filter-redirect');
const familyLabels = { 'system-transport': '系统运输', 'world-market': '世界交易', people: '人员与求救', maintenance: '系统维护' };
const palette = { ink: '#f5eed7', muted: '#b6b8a7', panel: 0x10231b, deep: 0x07120d, line: 0x628472, moss: 0xa7d97d, sun: 0xf1c765, danger: 0xef8074, blue: 0x8acb81 };

class ShelterScene extends Phaser.Scene {
  constructor() {
    super('ShelterScene');
    this.ui = [];
    this.buildings = new Map();
    this.verified = false;
    this.sandboxViewed = false;
  }

  preload() {
    this.load.image('base-day', './assets/base-day.webp');
  }

  create() {
    this.add.image(640, 360, 'base-day').setDisplaySize(1280, 720).setDepth(0);
    this.nightOverlay = this.add.rectangle(640, 360, 1280, 720, 0x071021, 0).setDepth(20);
    this.createWorldZones();
    this.setNight(false);
    this.render();
  }

  createWorldZones() {
    this.createWorldZone('command', 624, 233, 245, 158, '指挥室', '打开收件箱', () => this.open('inbox'));
    this.createWorldZone('radio', 176, 189, 157, 328, '无线电站', '核验档案与接收求助');
    this.createWorldZone('warehouse', 960, 229, 250, 210, '仓库', '储存物资与组件');
    this.createWorldZone('clinic', 713, 540, 190, 150, '医疗站', '处理伤员');
    this.createWorldZone('relay', 190, 467, 160, 160, '网络中继器', '保护通讯链路');
    this.createWorldZone('garden', 327, 328, 224, 165, '菜园用地', '未开发：需要蓝图、种子、劳动力与材料', null, 'expansion');
    this.createWorldZone('water', 965, 513, 225, 178, '净水设施用地', '未开发：需要蓝图、组件、劳动力与材料', null, 'expansion');
    this.createWorldZone('west-yard', 380, 487, 180, 190, '西侧扩建地块', '预留：未来可扩展防线或工坊', null, 'expansion');
    this.createWorldZone('east-yard', 1120, 480, 150, 190, '东侧扩建地块', '预留：未来可扩展设施', null, 'expansion');
  }

  createWorldZone(id, x, y, width, height, label, description, action = null, kind = 'building') {
    const color = kind === 'expansion' ? palette.blue : palette.sun;
    const frame = this.add.rectangle(x, y, width, height, color, 0).setStrokeStyle(3, color, 0).setDepth(8);
    const marker = this.add.circle(x + width / 2 - 14, y - height / 2 + 14, 7, color, 0).setDepth(9);
    const zone = this.add.zone(x, y, width, height).setDepth(10).setInteractive({ useHandCursor: true });
    zone.on('pointerover', () => {
      if (state.screen !== 'base') return;
      frame.setStrokeStyle(3, color, .92);
      marker.setAlpha(1);
      this.setHint(`${label} · ${description}`);
    });
    zone.on('pointerout', () => {
      if (!this.buildings.get(id)?.status) {
        frame.setStrokeStyle(3, color, 0);
        marker.setAlpha(0);
      }
    });
    zone.on('pointerdown', () => {
      if (state.screen !== 'base') return;
      this.setHint(`${label} · ${description}`);
      if (action) action();
    });
    this.buildings.set(id, { frame, marker, zone, label, description, kind, status: null });
  }

  setHint(text) {
    state.baseHint = text;
    this.hintText?.setText(text);
  }

  setNight(isNight) {
    state.night = isNight;
    this.nightOverlay.setAlpha(isNight ? .6 : 0);
  }

  setBuildingState(id, status) {
    const building = this.buildings.get(id);
    if (!building) return;
    building.status = status;
    const color = status === 'damaged' ? palette.danger : palette.moss;
    building.frame.setStrokeStyle(4, color, 1);
    building.marker.setFillStyle(color).setAlpha(1);
  }

  unlockExpansion(id) {
    this.setBuildingState(id, 'available');
  }

  open(screen) {
    state.screen = screen;
    this.render();
  }

  keep(...objects) {
    objects.forEach((object) => this.ui.push(object));
    return objects[objects.length - 1];
  }

  clearUi() {
    this.ui.forEach((object) => object.destroy());
    this.ui = [];
  }

  text(x, y, content, style = {}) {
    return this.keep(this.add.text(x, y, content, { fontFamily: 'system-ui, sans-serif', fontSize: '16px', color: palette.ink, ...style }).setDepth(30));
  }

  rect(x, y, width, height, color = palette.panel, alpha = .94, stroke = palette.line) {
    return this.keep(this.add.rectangle(x, y, width, height, color, alpha).setStrokeStyle(1, stroke, .9).setDepth(29));
  }

  button(x, y, width, height, label, onClick, tone = 'default', disabled = false) {
    const colors = { default: [0x183228, palette.line, palette.ink], moss: [palette.moss, palette.moss, '#102212'], danger: [palette.danger, palette.danger, '#2d0c08'], sun: [palette.sun, palette.sun, '#30250d'] };
    const [fill, stroke, textColor] = colors[tone];
    const box = this.keep(this.add.rectangle(x, y, width, height, fill, disabled ? .35 : 1).setStrokeStyle(1, stroke, .95).setDepth(31));
    const caption = this.text(x, y, label, { fontSize: '14px', fontStyle: 'bold', color: textColor }).setOrigin(.5);
    if (!disabled) {
      box.setInteractive({ useHandCursor: true });
      box.on('pointerover', () => box.setAlpha(.82));
      box.on('pointerout', () => box.setAlpha(1));
      box.on('pointerdown', onClick);
    }
  }

  render() {
    this.clearUi();
    this.buildings.forEach((building) => { building.zone.input.enabled = state.screen === 'base'; });
    this.drawHud();
    if (state.screen === 'base') this.drawBase();
    if (state.screen === 'inbox') this.drawInbox();
    if (state.screen === 'sandbox') this.drawSandbox();
    if (state.screen === 'report') this.drawReport();
    if (state.result) this.drawResult();
  }

  drawHud() {
    this.rect(640, 39, 1248, 58, palette.deep, .86);
    const stats = [`DAY ${String(state.day).padStart(2, '0')}`, `完整性 ${state.integrity}%`, `物资 ${state.supplies}`, `金币 ${state.coins}`, `情报 ${state.intel}`, `沙盒 ${state.sandboxUses}/1`];
    stats.forEach((value, index) => this.text(34 + index * 145, 28, value, { fontSize: '15px', fontStyle: 'bold', color: index === 1 && state.integrity < 50 ? '#ff9b91' : palette.ink }));
    this.button(1037, 39, 92, 30, '基地', () => this.open('base'), 'default', state.screen === 'base');
    this.button(1137, 39, 92, 30, `收件箱 ${state.unread}`, () => this.open('inbox'), 'default', state.screen === 'inbox');
    this.button(1230, 39, 76, 30, state.night ? '白天' : '夜晚', () => { this.setNight(!state.night); this.render(); }, 'sun');
  }

  drawBase() {
    this.rect(330, 654, 620, 84, palette.deep, .88);
    this.text(48, 623, '基地状态', { fontSize: '13px', color: palette.moss, fontStyle: 'bold' });
    this.hintText = this.text(48, 646, state.baseHint, { fontSize: '17px', wordWrap: { width: 540 } });
    this.text(48, 680, state.impact, { fontSize: '13px', color: palette.muted, wordWrap: { width: 540 } });
    this.button(1050, 650, 160, 38, `举报台${state.report ? ' · 新情报' : ''}`, () => this.open('report'), state.report ? 'moss' : 'default');
    this.button(1050, 695, 160, 30, '查看收件箱', () => this.open('inbox'), 'sun');
  }

  drawTerminal(title, subtitle) {
    this.rect(970, 395, 560, 620, palette.deep, .97);
    this.text(720, 110, subtitle, { fontSize: '12px', color: palette.moss, fontStyle: 'bold' });
    this.text(720, 132, title, { fontSize: '25px', fontStyle: 'bold', wordWrap: { width: 500 } });
    this.button(1225, 94, 46, 26, '关闭', () => this.open('base'), 'default');
  }

  drawInbox() {
    this.drawTerminal('收件箱', `${familyLabels[activeCard.family]} // 1 封待处理`);
    this.text(720, 188, activeCard.subject, { fontSize: '21px', fontStyle: 'bold', wordWrap: { width: 485 } });
    this.text(720, 250, activeCard.sender, { fontSize: '14px', color: palette.sun, wordWrap: { width: 485 } });
    this.text(720, 276, `接收时间 ${activeCard.time}`, { fontSize: '13px', color: palette.muted });
    this.text(720, 314, activeCard.paragraphs.join('\n\n'), { fontSize: '15px', lineSpacing: 6, wordWrap: { width: 485 } });
    const cost = activeCard.verificationCost ?? 2;
    if (this.verified) {
      this.text(720, 454, `核验结果：${activeCard.clue}`, { fontSize: '13px', color: palette.moss, wordWrap: { width: 485 } });
    } else {
      this.button(790, 470, 140, 32, `核验线索 · ${cost} 金币`, () => this.verify(), 'default', state.coins < cost || state.resolved);
    }
    if (state.resolved) {
      this.text(720, 548, '这封邮件已处理。结果会在基地状态中保留。', { fontSize: '15px', color: palette.muted, wordWrap: { width: 470 } });
      return;
    }
    const sandboxDisabled = activeCard.sandboxEligible === false || state.sandboxUses <= 0;
    this.button(788, 586, 136, 40, activeCard.acceptLabel ?? '接受并执行', () => this.resolve('accept'), 'danger');
    this.button(940, 586, 100, 40, '举报', () => this.resolve('report'), 'moss');
    this.button(1098, 586, 190, 40, activeCard.sandboxEligible === false ? '无可隔离载荷' : `沙盒 ${state.sandboxUses}/1`, () => this.useSandbox(), 'default', sandboxDisabled);
  }

  drawSandbox() {
    this.drawTerminal('隔离沙盒', 'ISOLATED ENVIRONMENT // 不访问真实链接');
    this.text(720, 194, activeCard.sandbox.join('\n\n'), { fontFamily: 'monospace', fontSize: '14px', color: '#d8f7d7', lineSpacing: 7, wordWrap: { width: 485 } });
    const safe = activeCard.truth === 'malicious' ? '✓ 沙盒已阻断异常行为。' : '✓ 未发现异常行为，仍应核对订单。';
    this.text(720, 394, safe, { fontSize: '15px', color: palette.moss });
    this.button(800, 590, 150, 40, '确认举报', () => this.resolve('report'), 'moss', !this.sandboxViewed || state.resolved);
    this.button(1010, 590, 150, 40, '返回邮件', () => this.open('inbox'), 'default');
  }

  drawReport() {
    this.drawTerminal('举报台', 'THREAT INTELLIGENCE');
    if (state.report) {
      this.text(720, 202, state.report.title, { fontSize: '19px', fontStyle: 'bold', wordWrap: { width: 485 } });
      this.text(720, 244, state.report.body, { fontSize: '15px', color: palette.muted, lineSpacing: 6, wordWrap: { width: 485 } });
    } else {
      this.text(720, 205, '暂无已提交的威胁情报。\n从收件箱或沙盒提交可疑邮件。', { fontSize: '16px', color: palette.muted, lineSpacing: 8 });
    }
    this.button(960, 590, 170, 40, '返回基地', () => this.open('base'), 'default');
  }

  verify() {
    const cost = activeCard.verificationCost ?? 2;
    if (state.coins < cost || state.resolved) return;
    state.coins -= cost;
    this.verified = true;
    this.render();
  }

  useSandbox() {
    if (state.resolved || activeCard.sandboxEligible === false || state.sandboxUses <= 0) return;
    state.sandboxUses -= 1;
    this.sandboxViewed = true;
    this.open('sandbox');
  }

  applyResources(resources = {}) {
    Object.entries(resources).forEach(([resource, amount]) => { state[resource] = Math.max(0, (state[resource] ?? 0) + amount); });
  }

  applyConstructionReward(reward) {
    if (!reward) return;
    reward.blueprints?.forEach((blueprint) => state.construction.blueprints.add(blueprint));
    Object.entries(reward.components ?? {}).forEach(([component, amount]) => { state.construction.components[component] = (state.construction.components[component] ?? 0) + amount; });
    state.construction.labour += reward.labour ?? 0;
    Object.entries(reward.materials ?? {}).forEach(([material, amount]) => { state.construction.materials[material] = (state.construction.materials[material] ?? 0) + amount; });
  }

  resolve(action) {
    if (state.resolved) return;
    const outcome = activeCard.outcomes[action];
    if (!outcome) return;
    state.resolved = true;
    state.unread = 0;
    this.applyResources(outcome.resources);
    this.applyConstructionReward(outcome.constructionReward);
    if (outcome.guaranteedNightEffect) state.guaranteedNightEffects.push(outcome.guaranteedNightEffect);
    if (outcome.retryAfterDays || outcome.marketBlacklistDays || outcome.followUp) state.deferredEvents.push({ cardId: activeCard.id, ...outcome });
    if (outcome.facility) this.setBuildingState(outcome.facility, outcome.facilityState);
    if (outcome.unlockExpansion) this.unlockExpansion(outcome.unlockExpansion);
    state.impact = outcome.impact;
    if (outcome.report) state.report = { title: activeCard.subject, body: outcome.report };
    state.result = { kind: outcome.kind, title: outcome.title, message: outcome.message, learning: outcome.learning };
    state.screen = outcome.report ? 'report' : 'base';
    this.render();
  }

  drawResult() {
    const x = state.screen === 'base' ? 640 : 335;
    this.rect(x, 182, 520, 184, state.result.kind === 'secured' ? 0x173321 : 0x3b1c18, .97, state.result.kind === 'secured' ? palette.moss : palette.danger);
    this.text(x - 232, 114, state.result.title, { fontSize: '20px', fontStyle: 'bold', wordWrap: { width: 460 } });
    this.text(x - 232, 150, state.result.message, { fontSize: '14px', color: palette.muted, wordWrap: { width: 460 } });
    this.text(x - 232, 199, `复盘：${state.result.learning}`, { fontSize: '13px', color: palette.ink, wordWrap: { width: 460 } });
    this.button(x + 185, 247, 76, 28, '明白', () => { state.result = null; this.render(); }, 'default');
  }
}

new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game-container',
  width: 1280,
  height: 720,
  backgroundColor: '#13271d',
  pixelArt: true,
  antialias: false,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: ShelterScene,
});
