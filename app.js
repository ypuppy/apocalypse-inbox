const DEVELOPER_MODE = true;
const DAY_START = 8 * 60;
const NIGHT_START = 21 * 60;

const state = {
  day: 1, clockMinutes: DAY_START, phase: 'day', defense: 82,
  supplies: 46, coins: 30, intel: 18, seeds: 0, sandboxUses: 1,
  unread: 1, currentCardId: 'shipment-water-filter-redirect', resolvedToday: false,
  screen: 'base', baseHint: '指挥室有一封待处理邮件。日落前做出决定。', impact: '无线电站正在接收外部请求。',
  report: null, pendingResolutions: [], processedMails: [], nightLog: [], scheduledEvents: [], seenEventIds: new Set(),
  facilityStatus: {}, security: { gate: true, alarm: true }, marketBlockedUntil: 0,
  construction: { blueprints: new Set(), components: {}, labour: 0, materials: { wood: 18, scrap: 28 } },
  builtFacilities: new Set(), buildTarget: null,
};

const familyLabels = { 'system-transport': '系统运输', 'world-market': '世界交易', people: '人员与求救', maintenance: '系统维护' };
const palette = { ink: '#f5eed7', muted: '#b6b8a7', panel: 0x10231b, deep: 0x07120d, line: 0x628472, moss: 0xa7d97d, sun: 0xf1c765, danger: 0xef8074, blue: 0x8acb81 };
const facilityLabels = { garden: '菜园', water: '净水设施', relay: '网络中继器', radio: '无线电站', clinic: '医疗站', warehouse: '仓库', gate: '西门闸门', alarm: '警报网络' };
const getCard = (id) => eventCards.find((card) => card.id === id);
const formatClock = (minutes) => `${String(Math.floor(minutes / 60) % 24).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;

class ShelterScene extends Phaser.Scene {
  constructor() {
    super('ShelterScene');
    this.ui = [];
    this.buildings = new Map();
    this.verified = false;
    this.sandboxViewed = false;
  }

  preload() { this.load.image('base-day', './assets/base-day.webp'); }

  create() {
    this.add.image(640, 360, 'base-day').setDisplaySize(1280, 720).setDepth(0);
    this.nightOverlay = this.add.rectangle(640, 360, 1280, 720, 0x071021, 0).setDepth(20);
    this.createWorldZones();
    this.time.addEvent({ delay: 1800, loop: true, callback: () => this.tickClock() });
    this.setNight(false);
    this.render();
  }

  createWorldZones() {
    this.createWorldZone('command', 624, 233, 245, 158, '指挥室', '打开收件箱', () => this.open('inbox'));
    this.createWorldZone('radio', 176, 189, 157, 328, '无线电站', '核验档案与接收求助');
    this.createWorldZone('warehouse', 960, 229, 250, 210, '仓库', '查看蓝图、组件与施工材料', () => this.openWarehouse());
    this.createWorldZone('clinic', 713, 540, 190, 150, '医疗站', '处理伤员');
    this.createWorldZone('relay', 190, 467, 160, 160, '网络中继器', '保护通讯链路');
    this.createWorldZone('gate', 625, 646, 190, 100, '西门闸门', '基础防线：提供 14 点防守加成');
    this.createWorldZone('garden', 327, 328, 224, 165, '菜园用地', '点击查看建造条件', () => this.openWarehouse('garden'), 'expansion');
    this.createWorldZone('water', 965, 513, 225, 178, '净水设施用地', '点击查看建造条件', () => this.openWarehouse('water'), 'expansion');
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
      frame.setStrokeStyle(3, color, .92); marker.setAlpha(1); this.setHint(`${label} · ${description}`);
    });
    zone.on('pointerout', () => {
      if (!this.buildings.get(id)?.status) { frame.setStrokeStyle(3, color, 0); marker.setAlpha(0); }
    });
    zone.on('pointerdown', () => { if (state.screen === 'base') { this.setHint(`${label} · ${description}`); action?.(); } });
    this.buildings.set(id, { frame, marker, zone, label, description, kind, status: state.facilityStatus[id] ?? null });
    if (state.facilityStatus[id]) this.setBuildingState(id, state.facilityStatus[id]);
  }

  tickClock() {
    if (state.phase !== 'day') return;
    state.clockMinutes += 10;
    if (state.clockMinutes >= NIGHT_START) { state.clockMinutes = NIGHT_START; this.settleNight(); return; }
    this.render();
  }

  setHint(text) { state.baseHint = text; this.hintText?.setText(text); }
  setNight(isNight) { this.nightOverlay.setAlpha(isNight ? .6 : 0); }

  setBuildingState(id, status) {
    state.facilityStatus[id] = status;
    if (id === 'gate') state.security.gate = status !== 'damaged';
    if (id === 'alarm') state.security.alarm = status !== 'damaged';
    const building = this.buildings.get(id);
    if (!building) return;
    building.status = status;
    const color = status === 'damaged' ? palette.danger : palette.moss;
    building.frame.setStrokeStyle(4, color, 1); building.marker.setFillStyle(color).setAlpha(1);
  }

  open(screen) { state.screen = screen; this.render(); }
  openWarehouse(target = null) { state.buildTarget = target; this.open('warehouse'); }
  keep(...objects) { objects.forEach((object) => this.ui.push(object)); return objects[objects.length - 1]; }
  clearUi() { this.ui.forEach((object) => object.destroy()); this.ui = []; }
  text(x, y, content, style = {}) { return this.keep(this.add.text(x, y, content, { fontFamily: 'system-ui, sans-serif', fontSize: '16px', color: palette.ink, ...style }).setDepth(30)); }
  rect(x, y, width, height, color = palette.panel, alpha = .94, stroke = palette.line) { return this.keep(this.add.rectangle(x, y, width, height, color, alpha).setStrokeStyle(1, stroke, .9).setDepth(29)); }

  button(x, y, width, height, label, onClick, tone = 'default', disabled = false) {
    const colors = { default: [0x183228, palette.line, palette.ink], moss: [palette.moss, palette.moss, '#102212'], danger: [palette.danger, palette.danger, '#2d0c08'], sun: [palette.sun, palette.sun, '#30250d'] };
    const [fill, stroke, textColor] = colors[tone];
    const box = this.keep(this.add.rectangle(x, y, width, height, fill, disabled ? .35 : 1).setStrokeStyle(1, stroke, .95).setDepth(31));
    this.text(x, y, label, { fontSize: '13px', fontStyle: 'bold', color: textColor }).setOrigin(.5).setDepth(32);
    if (!disabled) { box.setInteractive({ useHandCursor: true }); box.on('pointerover', () => box.setAlpha(.82)); box.on('pointerout', () => box.setAlpha(1)); box.on('pointerdown', onClick); }
  }

  render() {
    this.clearUi();
    this.buildings.forEach((building) => { building.zone.input.enabled = state.screen === 'base'; });
    this.drawHud();
    if (state.screen === 'base') this.drawBase();
    if (state.screen === 'inbox') this.drawInbox();
    if (state.screen === 'sandbox') this.drawSandbox();
    if (state.screen === 'report') this.drawReport();
    if (state.screen === 'archive') this.drawArchive();
    if (state.screen === 'warehouse') this.drawWarehouse();
    if (state.screen === 'night') this.drawNight();
  }

  drawHud() {
    this.rect(640, 39, 1248, 58, palette.deep, .86);
    const stats = [`DAY ${String(state.day).padStart(2, '0')} · ${formatClock(state.clockMinutes)}`, `防御 ${state.defense}`, `物资 ${state.supplies}`, `金币 ${state.coins}`, `情报 ${state.intel}`, `沙盒 ${state.sandboxUses}/1`];
    [34, 190, 315, 420, 525, 625].forEach((x, index) => this.text(x, 28, stats[index], { fontSize: '14px', fontStyle: 'bold', color: index === 1 && state.defense < 50 ? '#ff9b91' : palette.ink }));
    this.button(850, 39, 76, 30, '基地', () => this.open('base'), 'default', state.screen === 'base');
    this.button(934, 39, 100, 30, `收件箱 ${state.unread}`, () => this.open('inbox'), 'default', state.screen === 'inbox' || state.unread === 0);
    this.button(1043, 39, 90, 30, `归档 ${state.processedMails.length}`, () => this.open('archive'), 'default', state.screen === 'archive');
    if (DEVELOPER_MODE && state.phase === 'day') this.button(1185, 39, 130, 30, '测试：跳至夜晚', () => this.skipToNight(), 'sun');
    if (state.phase === 'night') this.text(1180, 28, '夜晚结算中', { fontSize: '14px', fontStyle: 'bold', color: palette.sun });
  }

  drawBase() {
    this.rect(350, 650, 620, 96, palette.deep, .9);
    this.text(350, 612, `基地状态 · ${state.phase === 'day' ? '白天行动' : '夜晚结算'}`, { fontSize: '13px', color: palette.moss, fontStyle: 'bold', align: 'center', wordWrap: { width: 560 } }).setOrigin(.5, 0);
    this.hintText = this.text(350, 637, state.baseHint, { fontSize: '17px', align: 'center', wordWrap: { width: 560 } }).setOrigin(.5, 0);
    this.text(350, 674, `${state.impact}\n闸门 ${state.security.gate ? '在线' : '受损'} · 警报网 ${state.security.alarm ? '在线' : '离线'}`, { fontSize: '13px', color: palette.muted, align: 'center', lineSpacing: 4, wordWrap: { width: 560 } }).setOrigin(.5, 0);
    this.button(930, 632, 124, 34, '仓库与建造', () => this.openWarehouse(), 'moss');
    this.button(1065, 632, 124, 34, `处理邮件 ${state.processedMails.length}`, () => this.open('archive'), 'default');
    this.button(930, 682, 124, 30, `举报台${state.report ? ' · 新' : ''}`, () => this.open('report'), state.report ? 'moss' : 'default');
    this.button(1065, 682, 124, 30, state.unread ? '查看收件箱' : '等待夜晚', () => this.open('inbox'), 'sun', !state.unread);
  }

  drawTerminal(title, subtitle) {
    this.rect(970, 395, 560, 620, palette.deep, .97);
    this.text(720, 110, subtitle, { fontSize: '12px', color: palette.moss, fontStyle: 'bold' });
    this.text(720, 132, title, { fontSize: '25px', fontStyle: 'bold', wordWrap: { width: 500 } });
    this.button(1225, 94, 46, 26, '关闭', () => this.open('base'), 'default');
  }

  drawInbox() {
    const card = getCard(state.currentCardId);
    this.drawTerminal('收件箱', card ? `${familyLabels[card.family]} // ${state.unread} 封待处理` : '今日没有待处理邮件');
    if (!card || !state.unread) {
      this.text(720, 214, '日间选择已经归档。所有奖励与后果会在夜晚统一结算。', { fontSize: '16px', color: palette.muted, wordWrap: { width: 480 } });
      this.button(960, 590, 180, 40, '查看已处理邮件', () => this.open('archive'), 'default'); return;
    }
    this.text(720, 188, card.subject, { fontSize: '21px', fontStyle: 'bold', wordWrap: { width: 485 } });
    this.text(720, 250, card.sender, { fontSize: '14px', color: palette.sun, wordWrap: { width: 485 } });
    this.text(720, 276, `接收时间 ${card.time}`, { fontSize: '13px', color: palette.muted });
    this.text(720, 314, card.paragraphs.join('\n\n'), { fontSize: '15px', lineSpacing: 6, wordWrap: { width: 485 } });
    const cost = card.verificationCost ?? 2;
    if (this.verified) this.text(720, 454, `核验线索：${card.clue}`, { fontSize: '13px', color: palette.moss, wordWrap: { width: 485 } });
    else this.button(790, 470, 140, 32, `核验线索 · ${cost} 金币`, () => this.verify(), 'default', state.coins < cost);
    this.button(788, 586, 136, 40, card.acceptLabel ?? '接受并执行', () => this.resolve('accept'), 'danger');
    this.button(940, 586, 100, 40, '举报', () => this.resolve('report'), 'moss');
    this.button(1098, 586, 190, 40, card.sandboxEligible === false ? '无可隔离载荷' : `沙盒 ${state.sandboxUses}/1`, () => this.useSandbox(), 'default', card.sandboxEligible === false || state.sandboxUses <= 0);
  }

  drawSandbox() {
    const card = getCard(state.currentCardId); if (!card) return this.open('inbox');
    this.drawTerminal('隔离沙盒', 'ISOLATED ENVIRONMENT // 不访问真实链接');
    this.text(720, 194, card.sandbox.join('\n\n'), { fontFamily: 'monospace', fontSize: '14px', color: '#d8f7d7', lineSpacing: 7, wordWrap: { width: 485 } });
    this.text(720, 394, card.truth === 'malicious' ? '✓ 沙盒已阻断异常行为。' : '✓ 未发现异常行为，仍应核对订单。', { fontSize: '15px', color: palette.moss });
    this.button(800, 590, 150, 40, '确认举报', () => this.resolve('report'), 'moss', !this.sandboxViewed);
    this.button(1010, 590, 150, 40, '返回邮件', () => this.open('inbox'), 'default');
  }

  drawReport() {
    this.drawTerminal('举报台', 'THREAT INTELLIGENCE');
    if (state.report) {
      this.text(720, 202, state.report.title, { fontSize: '19px', fontStyle: 'bold', wordWrap: { width: 485 } });
      this.text(720, 244, state.report.body, { fontSize: '15px', color: palette.muted, lineSpacing: 6, wordWrap: { width: 485 } });
    } else this.text(720, 205, '尚未在夜晚确认任何举报结果。\n提交的情报会在夜间结算后归档。', { fontSize: '16px', color: palette.muted, lineSpacing: 8 });
    this.button(960, 590, 170, 40, '返回基地', () => this.open('base'), 'default');
  }

  drawArchive() {
    this.drawTerminal('已处理邮件', 'ARCHIVE // 选择会在夜晚才揭晓');
    if (!state.processedMails.length) { this.text(720, 205, '还没有处理过的邮件。', { fontSize: '16px', color: palette.muted }); return; }
    state.processedMails.slice(0, 4).forEach((entry, index) => {
      const y = 196 + index * 96; const color = entry.status === '待夜间结算' ? palette.sun : entry.result?.kind === 'secured' ? palette.moss : palette.danger;
      this.rect(965, y + 30, 490, 78, 0x13291f, .82, color);
      this.text(730, y, `${entry.status} · 第 ${entry.day} 天`, { fontSize: '12px', color, fontStyle: 'bold' });
      this.text(730, y + 20, entry.subject, { fontSize: '15px', fontStyle: 'bold', wordWrap: { width: 450 } });
      this.text(730, y + 47, entry.status === '待夜间结算' ? `已选择：${entry.actionLabel}。等待日落。` : entry.result.message, { fontSize: '12px', color: palette.muted, wordWrap: { width: 450 } });
    });
  }

  drawWarehouse() {
    const target = state.buildTarget; this.drawTerminal(target ? `${facilityLabels[target]} · 建造准备` : '仓库与建造', 'WAREHOUSE // 蓝图、组件与施工物资');
    const blueprints = [...state.construction.blueprints].map((item) => item === 'garden-bed' ? '菜园图纸' : '净水器蓝图').join('、') || '暂无';
    const components = Object.entries(state.construction.components).filter(([, value]) => value > 0).map(([name, value]) => `${name === 'purifierCore' ? '净水器核心' : '滤芯外壳'} ×${value}`).join('、') || '暂无';
    this.text(720, 190, `蓝图：${blueprints}\n组件：${components}\n劳动力：${state.construction.labour}\n木材：${state.construction.materials.wood} · 废料：${state.construction.materials.scrap} · 种子：${state.seeds}`, { fontSize: '15px', lineSpacing: 8, wordWrap: { width: 485 } });
    (target ? [target] : ['garden', 'water']).forEach((id, index) => this.drawBuildOption(id, 462 + index * 88));
  }

  drawBuildOption(id, y) {
    const req = constructionRequirements[id]; const built = state.builtFacilities.has(id);
    const components = Object.entries(req.components).map(([name, count]) => `${name === 'purifierCore' ? '核心' : '外壳'}×${count}`).join('、') || '无';
    const blueprint = req.blueprint === 'garden-bed' ? '菜园图纸' : '净水器蓝图';
    const text = `需求：${blueprint} · 组件 ${components} · 劳动力 ${req.labour} · 木材 ${req.materials.wood} · 废料 ${req.materials.scrap}${req.seeds ? ` · 种子 ${req.seeds}` : ''}`;
    this.rect(965, y, 490, 76, 0x13291f, .82, built ? palette.moss : palette.line);
    this.text(730, y - 28, facilityLabels[id], { fontSize: '17px', fontStyle: 'bold' });
    this.text(730, y - 2, text, { fontSize: '12px', color: palette.muted, wordWrap: { width: 330 } });
    this.button(1138, y + 18, 130, 32, built ? '已建成' : '选择建造', () => this.buildFacility(id), built ? 'moss' : 'sun', built || !this.canBuild(id));
  }

  drawNight() {
    this.drawTerminal(`第 ${state.day} 天 · 夜晚结算`, 'NIGHT REPORT // 白天选择的结果现已确认');
    if (!state.nightLog.length) this.text(720, 200, '今晚暂时平静。', { fontSize: '16px', color: palette.muted });
    state.nightLog.slice(0, 5).forEach((entry, index) => {
      const y = 190 + index * 72; const color = entry.kind === 'secured' ? palette.moss : entry.kind === 'attack' ? palette.danger : palette.sun;
      this.text(720, y, entry.title, { fontSize: '15px', color, fontStyle: 'bold', wordWrap: { width: 485 } });
      this.text(720, y + 24, entry.message, { fontSize: '13px', color: palette.muted, wordWrap: { width: 485 } });
    });
    this.button(970, 590, 190, 40, `开始第 ${state.day + 1} 天`, () => this.startNextDay(), 'sun');
  }

  verify() {
    const card = getCard(state.currentCardId); const cost = card?.verificationCost ?? 2;
    if (!card || state.coins < cost) return; state.coins -= cost; this.verified = true; this.render();
  }

  useSandbox() {
    const card = getCard(state.currentCardId);
    if (!card || card.sandboxEligible === false || state.sandboxUses <= 0) return;
    state.sandboxUses -= 1; this.sandboxViewed = true; this.open('sandbox');
  }

  applyResources(resources = {}) { Object.entries(resources).forEach(([resource, amount]) => { state[resource] = Math.max(0, (state[resource] ?? 0) + amount); }); }
  applyConstructionReward(reward) {
    if (!reward) return;
    reward.blueprints?.forEach((blueprint) => state.construction.blueprints.add(blueprint));
    Object.entries(reward.components ?? {}).forEach(([component, amount]) => { state.construction.components[component] = (state.construction.components[component] ?? 0) + amount; });
    state.construction.labour += reward.labour ?? 0;
    Object.entries(reward.materials ?? {}).forEach(([material, amount]) => { state.construction.materials[material] = (state.construction.materials[material] ?? 0) + amount; });
  }

  resolve(action) {
    const card = getCard(state.currentCardId); const outcome = card?.outcomes[action];
    if (!card || !outcome || state.resolvedToday || state.phase !== 'day') return;
    state.resolvedToday = true; state.unread = 0; state.seenEventIds.add(card.id);
    const archiveEntry = { cardId: card.id, day: state.day, subject: card.subject, actionLabel: action === 'accept' ? (card.acceptLabel ?? '接受并执行') : '举报', status: '待夜间结算', result: null };
    state.pendingResolutions.push({ card, outcome, archiveEntry }); state.processedMails.unshift(archiveEntry);
    state.impact = '邮件已归档；日落后才会确认发货、陷阱与袭击后果。'; state.baseHint = '白天的选择已经锁定。你可以查看仓库、归档，或等待夜晚。'; state.screen = 'base'; this.render();
  }

  skipToNight() { if (state.phase === 'day') { state.clockMinutes = NIGHT_START; this.settleNight(); } }

  settleNight() {
    if (state.phase !== 'day') return;
    state.phase = 'night'; this.setNight(true); state.nightLog = [];
    state.pendingResolutions.splice(0).forEach((entry) => this.settleResolution(entry));
    this.resolveGuaranteedEffects(); this.resolveMutantRaid();
    state.baseHint = '夜晚结算已完成。黎明后会有新的邮件与世界状态。'; state.screen = 'night'; this.render();
  }

  settleResolution(entry) {
    const { card, outcome, archiveEntry } = entry;
    this.applyResources(outcome.resources); this.applyConstructionReward(outcome.constructionReward);
    if (outcome.facility) this.setBuildingState(outcome.facility, outcome.facilityState);
    if (outcome.report) state.report = { title: card.subject, body: outcome.report };
    if (outcome.guaranteedNightEffect) state.scheduledEvents.push({ type: 'guaranteed-effect', effect: outcome.guaranteedNightEffect, dueDay: state.day });
    if (outcome.retryAfterDays) state.scheduledEvents.push({ type: 'retry', eventId: card.id, dueDay: state.day + outcome.retryAfterDays });
    if (outcome.marketBlacklistDays) state.marketBlockedUntil = state.day + outcome.marketBlacklistDays;
    if (outcome.followUp) state.scheduledEvents.push({ type: 'ally-fall-check', followUp: outcome.followUp, dueDay: state.day });
    archiveEntry.status = '已结算'; archiveEntry.result = { kind: outcome.kind, title: outcome.title, message: outcome.message, learning: outcome.learning };
    state.impact = outcome.impact ?? state.impact; state.nightLog.push({ kind: outcome.kind, title: outcome.title, message: outcome.message });
    if (outcome.retryAfterDays) state.nightLog.push({ kind: 'notice', title: '运输信誉延迟', message: `该来源最早会在第 ${state.day + outcome.retryAfterDays} 天再次联络。` });
    if (outcome.marketBlacklistDays) state.nightLog.push({ kind: 'notice', title: '商家临时拉黑', message: `世界交易在第 ${state.marketBlockedUntil} 天前不会接受新的购买请求。` });
  }

  resolveGuaranteedEffects() {
    const due = state.scheduledEvents.filter((item) => item.dueDay === state.day && (item.type === 'guaranteed-effect' || item.type === 'ally-fall-check'));
    state.scheduledEvents = state.scheduledEvents.filter((item) => !due.includes(item));
    due.forEach((item) => item.type === 'guaranteed-effect' ? this.applyGuaranteedEffect(item.effect) : this.resolveAllyFall(item.followUp));
  }

  applyGuaranteedEffect(effect) {
    if (effect.type === 'unauthorized-requisition') {
      this.applyResources({ supplies: -12 }); this.setBuildingState('relay', 'damaged');
      state.nightLog.push({ kind: 'attack', title: '人为攻击：伪造征调生效', message: '攻击者利用泄露的会话从仓库转走 12 点物资，并继续干扰中继器。' });
    }
    if (effect.type === 'device-disruption') {
      const target = effect.targets.includes('relay') ? 'relay' : effect.targets[0]; this.setBuildingState(target, 'damaged');
      if (target === 'relay') this.setBuildingState('alarm', 'damaged');
      state.nightLog.push({ kind: 'attack', title: '人为攻击：设备干扰', message: `${facilityLabels[target] ?? target} 被远程干扰；${target === 'relay' ? '警报网络已离线。' : '夜间监测能力下降。'}` });
    }
    if (effect.type === 'market-drain') {
      this.applyResources({ coins: -6 }); state.marketBlockedUntil = Math.max(state.marketBlockedUntil, state.day + 3);
      state.nightLog.push({ kind: 'attack', title: '人为攻击：市场账户冻结', message: '攻击者从市场余额再转走 6 金币；世界交易暂时冻结。' });
    }
    if (effect.type === 'location-exposed') {
      this.applyResources({ defense: -14 }); this.setBuildingState('gate', 'damaged');
      state.nightLog.push({ kind: 'attack', title: '人为攻击：精准夜袭', message: '敌人利用泄露的防线情报破坏西门闸门，基地防御力 -14。' });
    }
  }

  resolveAllyFall(followUp) {
    if (Math.random() >= followUp.chance) { state.nightLog.push({ kind: 'notice', title: '白桦营地仍在坚持', message: '他们暂时没有失守，但无线电信号仍然微弱。' }); return; }
    state.scheduledEvents.push({ type: 'forced-card', eventId: followUp.eventId, dueDay: state.day + 1 });
    state.nightLog.push({ kind: 'attack', title: '白桦营地失守', message: '敌人占领了营地。明天可能会借用他们真实的联络身份发来信息。' });
  }

  resolveMutantRaid() {
    if (Math.random() >= nightRules.mutantRaidChance) { state.nightLog.push({ kind: 'notice', title: '改造人没有靠近围栏', message: '今晚没有发现大规模游荡群。' }); return; }
    const bonus = (state.security.gate ? 14 : 0) + (state.security.alarm ? 12 : 0); const effectiveDefense = state.defense + bonus;
    const attackStrength = 72 + state.day * 2 + Phaser.Math.Between(0, 12);
    if (effectiveDefense >= attackStrength) { state.nightLog.push({ kind: 'secured', title: '改造人袭击被击退', message: `袭击强度 ${attackStrength}，有效防守 ${effectiveDefense}。闸门与警报网守住了外围。` }); return; }
    const damage = Math.min(18, attackStrength - effectiveDefense + 6); this.applyResources({ defense: -damage, supplies: -4 });
    const target = state.security.gate ? 'clinic' : 'warehouse'; this.setBuildingState(target, 'damaged');
    state.nightLog.push({ kind: 'attack', title: '改造人突破外围', message: `袭击强度 ${attackStrength} 超过有效防守 ${effectiveDefense}；防御力 -${damage}，${facilityLabels[target]}受损，物资 -4。` });
  }

  startNextDay() {
    state.day += 1; state.clockMinutes = DAY_START; state.phase = 'day'; state.sandboxUses = 1; state.resolvedToday = false; state.buildTarget = null;
    this.verified = false; this.sandboxViewed = false; this.setNight(false);
    const card = this.selectNextCard(); state.currentCardId = card?.id ?? null; state.unread = card ? 1 : 0;
    state.baseHint = card ? '指挥室收到一封新邮件。日落前做出决定。' : '今日没有新邮件。你可以整理仓库并等待夜晚。';
    state.impact = card ? '无线电站转发了新的外部请求。' : '基地暂时没有新的外部联络。'; state.screen = 'base'; this.render();
  }

  selectNextCard() {
    const forced = state.scheduledEvents.find((item) => item.type === 'forced-card' && item.dueDay <= state.day);
    if (forced) { state.scheduledEvents = state.scheduledEvents.filter((item) => item !== forced); return getCard(forced.eventId); }
    const retry = state.scheduledEvents.find((item) => item.type === 'retry' && item.dueDay <= state.day);
    if (retry) { state.scheduledEvents = state.scheduledEvents.filter((item) => item !== retry); return getCard(retry.eventId); }
    return getEligibleEventCards(state.day).find((card) => !card.triggerOnly && !state.seenEventIds.has(card.id));
  }

  canBuild(id) {
    const req = constructionRequirements[id];
    if (!req || state.builtFacilities.has(id) || !state.construction.blueprints.has(req.blueprint) || state.construction.labour < req.labour || state.seeds < (req.seeds ?? 0)) return false;
    if (Object.entries(req.components).some(([name, amount]) => (state.construction.components[name] ?? 0) < amount)) return false;
    return Object.entries(req.materials).every(([name, amount]) => state.construction.materials[name] >= amount);
  }

  buildFacility(id) {
    if (!this.canBuild(id) || state.phase !== 'day') return;
    const req = constructionRequirements[id];
    Object.entries(req.components).forEach(([name, amount]) => { state.construction.components[name] -= amount; });
    Object.entries(req.materials).forEach(([name, amount]) => { state.construction.materials[name] -= amount; });
    state.seeds -= req.seeds ?? 0; state.builtFacilities.add(id); this.setBuildingState(id, 'upgraded');
    state.baseHint = `${facilityLabels[id]}已开始运作。扩建地块现在成为基地的一部分。`; state.impact = `仓库已为${facilityLabels[id]}发放蓝图、组件与施工材料。`; state.buildTarget = id; this.render();
  }
}

new Phaser.Game({
  type: Phaser.AUTO, parent: 'game-container', width: 1280, height: 720, backgroundColor: '#13271d', pixelArt: true, antialias: false,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }, scene: ShelterScene,
});
