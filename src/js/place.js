/** Komponenta stránky jedné země.
 *
 *  Vzory tabulky (hledání, filtr, stránkování) jsou z dokumentace Flowbite,
 *  chování řídí Alpine. Flowbite `data-*` je jen ve statickém markupu
 *  dropdownů, nikdy uvnitř `x-for` — pravidlo flowbite/dynamic.
 *
 *  Proti hlavní stránce se tady **nedávkuje**: největší země má stovku
 *  položek, ne tisícovku, takže stránkování po padesáti je levnější
 *  i srozumitelnější než nekonečný scroll.
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('place', () => ({
    rows: window.__PLACE__.rows,
    taxonomy: window.__PLACE__.groups,
    labels: window.__PLACE__.labels,

    q: '', topic: '', access: '', page: 1, perPage: 50,
    // Výchozí je abeceda, ne pořadí z katalogu: to je pořadí vzniku položek
    // a pro čtenáře nic neznamená.
    sort: { key: 'name', dir: 1 },
    theme: 'system',

    init() {
      this.theme = document.documentElement.getAttribute('data-theme') || 'system';
      this.readHash();
      // Jednou a hned, ne v $nextTick — dropdowny jsou ve statickém markupu
      // a čekat na Alpine by je nechalo na vteřinu mrtvé.
      if (window.initFlowbite) window.initFlowbite();
      for (const k of ['q', 'topic', 'access', 'page'])
        this.$watch(k, () => this.writeHash());
    },

    /** Filtr žije v URL, aby šel výřez poslat dál. V hashi stojí identifikátor
     *  tématu, ne popisek: popisky se přepisují a starý odkaz by tiše přestal
     *  filtrovat. */
    readHash(raw) {
      const p = new URLSearchParams(String(raw ?? location.hash ?? '').replace(/^#/, ''));
      this.q = p.get('q') || '';
      this.topic = this.rows.some(r => r.topic === p.get('topic')) ? p.get('topic') : '';
      this.access = this.rows.some(r => r.access === p.get('access')) ? p.get('access') : '';
      const page = parseInt(p.get('page'), 10);
      this.page = page > 0 ? page : 1;
      return { q: this.q, topic: this.topic, access: this.access, page: this.page };
    },

    writeHash() {
      const p = new URLSearchParams();
      if (this.q) p.set('q', this.q);
      if (this.topic) p.set('topic', this.topic);
      if (this.access) p.set('access', this.access);
      if (this.page > 1) p.set('page', String(this.page));
      const hash = p.toString();
      // V try: pod file:// a v sandboxu replaceState vyhodí výjimku a ta by
      // uvnitř $watch shodila reaktivitu celé stránky.
      try { history.replaceState(null, '', hash ? '#' + hash : '#'); } catch (e) { /* URL je bonus */ }
      return hash;
    },

    topicLabel(id) { return this.labels.topics[id] || id; },
    accessLabel(k) { return this.labels.access[k] || k; },
    dataLabel(k) { return this.labels.data[k] || k; },

    /** Témata, která země opravdu má, v pořadí číselníku. */
    get topics() {
      const n = new Map();
      for (const r of this.rows) n.set(r.topic, (n.get(r.topic) || 0) + 1);
      return this.taxonomy.flatMap(g => g.topics)
        .filter(t => n.has(t.id))
        .map(t => ({ id: t.id, label: t.label, count: n.get(t.id) }));
    },
    /** Skupiny včetně témat s nulou: díra v pokrytí je informace, ne důvod
     *  položku schovat. Stejné pravidlo jako v panelu hlavní stránky. */
    get groups() {
      const n = new Map();
      for (const r of this.rows) n.set(r.topic, (n.get(r.topic) || 0) + 1);
      return this.taxonomy.map(g => ({
        label: g.label,
        topics: g.topics.map(t => ({ id: t.id, label: t.label, count: n.get(t.id) || 0 })),
      }));
    },
    get accesses() {
      const n = new Map();
      for (const r of this.rows) n.set(r.access, (n.get(r.access) || 0) + 1);
      return [...n].map(([k, count]) => ({ k, label: this.accessLabel(k), count }))
        .sort((a, b) => b.count - a.count);
    },

    get filtered() {
      const q = this.q.trim().toLowerCase();
      const out = this.rows.filter(r =>
        (!this.topic || r.topic === this.topic)
        && (!this.access || r.access === this.access)
        && (!q || r.s.includes(q)));
      const { key, dir } = this.sort;
      return out.sort((a, b) => {
        // 'ord' je pořadí z katalogu, tedy číslo. Textové porovnání by
        // položku 100 zařadilo před 99.
        if (key === 'ord') return ((+a.ord || 0) - (+b.ord || 0)) * dir;
        const va = key === 'topic' ? this.topicLabel(a.topic)
                 : key === 'access' ? this.accessLabel(a.access)
                 : key === 'data' ? this.dataLabel(a.data) : a[key];
        const vb = key === 'topic' ? this.topicLabel(b.topic)
                 : key === 'access' ? this.accessLabel(b.access)
                 : key === 'data' ? this.dataLabel(b.data) : b[key];
        return String(va ?? '').localeCompare(String(vb ?? ''), 'cs') * dir;
      });
    },

    sortBy(key) {
      this.sort = this.sort.key === key ? { key, dir: -this.sort.dir } : { key, dir: 1 };
      this.page = 1;
    },

    get lastPage() { return Math.max(1, Math.ceil(this.filtered.length / this.perPage)); },
    get from() { return (Math.min(this.page, this.lastPage) - 1) * this.perPage; },
    get to() { return Math.min(this.from + this.perPage, this.filtered.length); },
    get shown() { return this.filtered.slice(this.from, this.to); },
    /** Čísla stránek bez elips. Ani největší země jich při padesáti na
     *  stránku nemá tolik, aby se řádek neuvezl — a kdyby vyrostla,
     *  stránkování se zalomí (flex-wrap), ne rozjede do strany. */
    get pages() { return Array.from({ length: this.lastPage }, (_, i) => i + 1); },

    scrollToTable() {
      const el = document.getElementById('table-search');
      if (el && el.scrollIntoView) el.scrollIntoView({ block: 'center', behavior: 'auto' });
    },

    /** Odznaky u popisu: strojová dostupnost a překážka v přístupu. Stejný
     *  klíč jako na hlavní stránce, aby se čtenář nemusel přeučovat.
     *
     *  Odznak pro `check: "anti-bot"` tu **není**: to pole žije jen ve
     *  `data/sources/*.json` a čte ho `tools/check_links.py`, do
     *  `data/catalog.csv` se nepropisuje. Dokud tam není sloupec, byla by
     *  to větev, která se nikdy nevykreslí. */
    marks(r) {
      const out = [];
      const bulk = { bulk: 'hromadně', api: 'API', ogc: 'OGC', download: 'ke stažení' }[r.data];
      if (bulk) out.push({ text: bulk, cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300' });
      const block = { paid: 'placené', registration: 'registrace', restricted: 'omezené' }[r.access];
      if (block) out.push({ text: block, cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' });
      return out;
    },

    /** Světlý → tmavý → podle systému. Tři stavy, protože „podle systému" je
     *  volba, ne absence volby; návrat na systém atribut odstraní, jinak by
     *  přestala platit media query. */
    cycleTheme() {
      this.theme = { light: 'dark', dark: 'system', system: 'light' }[this.theme];
      const root = document.documentElement;
      if (this.theme === 'system') root.removeAttribute('data-theme');
      else root.setAttribute('data-theme', this.theme);
      try {
        if (this.theme === 'system') localStorage.removeItem('geodata-atlas-theme');
        else localStorage.setItem('geodata-atlas-theme', this.theme);
      } catch (e) { /* v přísném sandboxu localStorage není */ }
    },
    get themeLabel() {
      return { light: 'světlý', dark: 'tmavý', system: 'podle systému' }[this.theme];
    },
  }));
});
