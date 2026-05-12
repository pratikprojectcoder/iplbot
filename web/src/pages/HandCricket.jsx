import { useState, useCallback } from 'react'

const IPL_TEAMS = {
  'Chennai Super Kings':       { short: 'CSK', color: '#FFCB05', emoji: '🦁' },
  'Mumbai Indians':            { short: 'MI',  color: '#004BA0', emoji: '🔵' },
  'Royal Challengers Bengaluru':{ short: 'RCB', color: '#D4213D', emoji: '🔴' },
  'Kolkata Knight Riders':     { short: 'KKR', color: '#3A225D', emoji: '💜' },
  'Delhi Capitals':            { short: 'DC',  color: '#004C93', emoji: '🔷' },
  'Rajasthan Royals':          { short: 'RR',  color: '#EA1A85', emoji: '👑' },
  'Punjab Kings':              { short: 'PBKS',color: '#DD1F2D', emoji: '🦁' },
  'Sunrisers Hyderabad':       { short: 'SRH', color: '#F26522', emoji: '🌅' },
  'Gujarat Titans':            { short: 'GT',  color: '#1C7ED6', emoji: '⚡' },
  'Lucknow Super Giants':      { short: 'LSG', color: '#A72056', emoji: '🦸' },
}

const TEAM_NAMES = Object.keys(IPL_TEAMS)

function initState() {
  return {
    phase: 'setup',
    userTeam: null, cpuTeam: null,
    tossWinner: null, userBatting: null, currentBatting: null,
    innings: 1,
    runs: 0, wickets: 0, balls: 0, ballLog: [],
    inn1Runs: 0, inn1Wkts: 0, inn1Balls: 0, inn1Log: [],
    inn2Runs: 0, inn2Wkts: 0, inn2Balls: 0, inn2Log: [],
    target: null, maxOvers: 5, maxWkts: 3,
    commentary: '', gameOver: false, winner: null,
  }
}

const COMMENTS = {
  out: n => ['🔴 WICKET! Both picked ' + n + '! Back to the pavilion!', '💥 OUT! Same number ' + n + '! Huge wicket!', '☝️ GONE! Matched at ' + n + '! The crowd goes wild!'],
  six: t => ['🚀 SIX! ' + t + ' smashes it out of the park!', '💥 MAXIMUM! That\'s gone into the stands! 6 runs!', '🏟️ What a shot! Sailed way over the ropes!'],
  four: t => ['🏏 FOUR! Beautifully timed through the gap!', '💫 Boundary! Races to the rope! 4 runs!', '🔥 FOUR! Cracking shot from ' + t + '!'],
  dot: () => ['⚫ Dot ball! Tight bowling, no run.', '🎯 Good delivery! Batter beaten!'],
  run: (n, t) => ['✅ ' + n + ' run' + (n > 1 ? 's' : '') + '! Good cricket from ' + t + '.', '🏃 ' + n + ' added to the total. Smart batting!'],
}

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)] }
function randInt(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a }
function overs(balls) { return `${Math.floor(balls / 6)}.${balls % 6}` }

function BallBubble({ val }) {
  let cls = 'ball '
  if (val === 'W') cls += 'ball-out'
  else if (val === 6) cls += 'ball-six'
  else if (val === 4) cls += 'ball-four'
  else if (val === 0) cls += 'ball-dot'
  else cls += 'ball-run'
  return <span className={cls}>{val === 'W' ? 'W' : val === 0 ? '•' : val}</span>
}

export default function HandCricket() {
  const [g, setG] = useState(initState())

  const update = useCallback(patch => setG(prev => ({ ...prev, ...(typeof patch === 'function' ? patch(prev) : patch) })), [])
  const reset  = () => setG(initState())

  // ─── SETUP phase ──────────────────────────────────────
  if (g.phase === 'setup') {
    return (
      <div className="fade-in">
        <div className="hc-title">🏏 IPL Hand Cricket</div>
        <div className="hc-sub">Pick a number 1–6 · Matching numbers = WICKET!</div>

        <div className="card" style={{ maxWidth: 600, margin: '0 auto' }}>
          <div className="section-title">🏟️ Match Setup</div>
          <div className="form-row">
            <div className="form-group">
              <label>Your Team</label>
              <select value={g.userTeam || TEAM_NAMES[0]} onChange={e => update({ userTeam: e.target.value })}>
                {TEAM_NAMES.map(t => <option key={t} value={t}>{IPL_TEAMS[t].emoji} {t}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Opponent</label>
              <select value={g.cpuTeam || TEAM_NAMES[1]} onChange={e => update({ cpuTeam: e.target.value })}>
                {TEAM_NAMES.filter(t => t !== (g.userTeam || TEAM_NAMES[0])).map(t => <option key={t} value={t}>{IPL_TEAMS[t].emoji} {t}</option>)}
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Overs per Innings</label>
              <select value={g.maxOvers} onChange={e => update({ maxOvers: Number(e.target.value) })}>
                {[2, 3, 5, 10, 20].map(o => <option key={o} value={o}>{o} overs</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Wickets per Innings</label>
              <select value={g.maxWkts} onChange={e => update({ maxWkts: Number(e.target.value) })}>
                {[1, 2, 3, 5, 10].map(w => <option key={w} value={w}>{w} wicket{w > 1 ? 's' : ''}</option>)}
              </select>
            </div>
          </div>
          <button className="btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} onClick={() => {
            const uTeam = g.userTeam || TEAM_NAMES[0]
            const cTeam = g.cpuTeam  || TEAM_NAMES[1]
            update({ ...initState(), userTeam: uTeam, cpuTeam: cTeam, maxOvers: g.maxOvers, maxWkts: g.maxWkts, phase: 'toss' })
          }}>
            ⚡ Start Match
          </button>
        </div>
      </div>
    )
  }

  // ─── TOSS phase ────────────────────────────────────────
  if (g.phase === 'toss') {
    const ui = IPL_TEAMS[g.userTeam]
    const ci = IPL_TEAMS[g.cpuTeam]
    return (
      <div className="fade-in">
        <div className="hc-title">🏏 IPL Hand Cricket</div>
        <div className="scoreboard" style={{ maxWidth: 520, margin: '0 auto 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '2.5rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem' }}>{ui.emoji}</div>
              <div style={{ color: '#ffd700', fontWeight: 700, fontFamily: 'Outfit' }}>{ui.short}</div>
              <div style={{ color: '#9ca3af', fontSize: '0.78rem' }}>You</div>
            </div>
            <div className="vs-badge">VS</div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem' }}>{ci.emoji}</div>
              <div style={{ color: '#ffd700', fontWeight: 700, fontFamily: 'Outfit' }}>{ci.short}</div>
              <div style={{ color: '#9ca3af', fontSize: '0.78rem' }}>CPU</div>
            </div>
          </div>
        </div>

        <div className="card" style={{ maxWidth: 480, margin: '0 auto' }}>
          <div className="section-title">🪙 Toss Time!</div>
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label>Your call</label>
            <select value={g._tossCall || 'Heads'} onChange={e => update({ _tossCall: e.target.value })}>
              <option value="Heads">Heads</option>
              <option value="Tails">Tails</option>
            </select>
          </div>
          <button className="btn-primary" style={{ width: '100%' }} onClick={() => {
            const coin   = pick(['Heads', 'Tails'])
            const userWon = (g._tossCall || 'Heads') === coin
            if (!userWon) {
              const cpuChoice = pick(['bat', 'bowl'])
              const userBatting = cpuChoice === 'bowl'
              update({ tossWinner: 'cpu', userBatting, currentBatting: userBatting ? 'user' : 'cpu', phase: 'playing', commentary: `${IPL_TEAMS[g.cpuTeam].short} won the toss and chose to ${cpuChoice} first! (Coin: ${coin})` })
            } else {
              update({ tossWinner: 'user', _tossMsg: `It's ${coin}! You won the toss!` })
            }
          }}>
            🪙 Flip the Coin!
          </button>

          {g._tossMsg && (
            <div className="fade-in" style={{ marginTop: '1rem' }}>
              <div className="banner-success banner" style={{ marginBottom: '1rem' }}>{g._tossMsg}</div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button className="btn-primary" style={{ flex: 1 }} onClick={() => update({ userBatting: true, currentBatting: 'user', phase: 'playing', _tossMsg: null })}>
                  🏏 Bat First
                </button>
                <button className="btn-ghost" style={{ flex: 1 }} onClick={() => update({ userBatting: false, currentBatting: 'cpu', phase: 'playing', _tossMsg: null })}>
                  🎯 Bowl First
                </button>
              </div>
            </div>
          )}
          {g.commentary && !g._tossMsg && (
            <div className="commentary-box" style={{ marginTop: '1rem' }}>{g.commentary}</div>
          )}
        </div>
      </div>
    )
  }

  // ─── PLAYING phase ─────────────────────────────────────
  if (g.phase === 'playing') {
    const ui = IPL_TEAMS[g.userTeam]
    const ci = IPL_TEAMS[g.cpuTeam]
    const isUserBatting = g.currentBatting === 'user'
    const batTeam = isUserBatting ? g.userTeam : g.cpuTeam
    const batInfo = IPL_TEAMS[batTeam]

    const inningsOver =
      g.balls >= g.maxOvers * 6 ||
      g.wickets >= g.maxWkts ||
      (g.target != null && g.runs >= g.target)

    function playBall(userNum) {
      const cpuNum = randInt(1, 6)
      const isOut  = userNum === cpuNum

      setG(prev => {
        let { runs, wickets, balls, ballLog, innings, inn1Runs, inn1Wkts, inn1Balls, inn1Log } = prev
        let commentary = ''

        if (isOut) {
          wickets++; balls++; ballLog = [...ballLog, 'W']
          commentary = pick(COMMENTS.out(userNum))
        } else {
          const scored = isUserBatting ? userNum : cpuNum
          runs += scored; balls++; ballLog = [...ballLog, scored]
          if (scored === 6) commentary = pick(COMMENTS.six(batInfo.short))
          else if (scored === 4) commentary = pick(COMMENTS.four(batInfo.short))
          else if (scored === 0) commentary = pick(COMMENTS.dot())
          else commentary = pick(COMMENTS.run(scored, batInfo.short))
        }

        const thisInningsOver =
          balls >= prev.maxOvers * 6 ||
          wickets >= prev.maxWkts ||
          (prev.target != null && runs >= prev.target)

        if (thisInningsOver) {
          if (innings === 1) {
            return {
              ...prev, runs, wickets, balls, ballLog, commentary,
              inn1Runs: runs, inn1Wkts: wickets, inn1Balls: balls, inn1Log: ballLog,
              target: runs + 1, innings: 2,
              runs: 0, wickets: 0, balls: 0, ballLog: [],
              currentBatting: prev.currentBatting === 'user' ? 'cpu' : 'user',
              phase: 'break',
            }
          } else {
            const firstBat  = prev.userBatting ? prev.userTeam : prev.cpuTeam
            const secondBat = prev.userBatting ? prev.cpuTeam  : prev.userTeam
            let winner
            if (runs >= prev.target) winner = secondBat
            else if (inn1Runs > runs) winner = firstBat
            else winner = 'Tie'
            return {
              ...prev, runs, wickets, balls, ballLog, commentary,
              inn2Runs: runs, inn2Wkts: wickets, inn2Balls: balls, inn2Log: ballLog,
              gameOver: true, winner, phase: 'result',
            }
          }
        }
        return { ...prev, runs, wickets, balls, ballLog, commentary }
      })
    }

    return (
      <div className="fade-in">
        <div className="hc-title">🏏 IPL Hand Cricket</div>

        {/* Scoreboard */}
        <div className="scoreboard" style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.72rem', color: '#9ca3af' }}>{isUserBatting ? '🏏 BATTING' : '🎯 BOWLING'}</div>
              <div style={{ fontSize: '1.4rem' }}>{ui.emoji} {ui.short}</div>
            </div>
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div className="innings-label">INNINGS {g.innings} · {batInfo.short} Batting</div>
              <div className="score-big">{g.runs}/{g.wickets}</div>
              <div className="score-label">{overs(g.balls)} / {g.maxOvers}.0 ov</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.72rem', color: '#9ca3af' }}>{isUserBatting ? '🎯 BOWLING' : '🏏 BATTING'}</div>
              <div style={{ fontSize: '1.4rem' }}>{ci.emoji} {ci.short}</div>
            </div>
          </div>
        </div>

        {/* Target banner */}
        {g.target != null && (
          <div className="target-banner">
            🎯 Target: {g.target} | Need {Math.max(0, g.target - g.runs)} from {Math.max(0, g.maxOvers * 6 - g.balls)} balls
            {g.balls < g.maxOvers * 6 && ` | RRR: ${((Math.max(0, g.target - g.runs)) / Math.max(1, g.maxOvers * 6 - g.balls) * 6).toFixed(1)}`}
          </div>
        )}

        {/* Ball log */}
        {g.ballLog.length > 0 && (
          <div className="ball-log" style={{ justifyContent: 'center' }}>
            {g.ballLog.slice(-12).map((b, i) => <BallBubble key={i} val={b} />)}
          </div>
        )}

        {/* Commentary */}
        {g.commentary && <div className="commentary-box">{g.commentary}</div>}

        {/* Play buttons */}
        {!inningsOver && (
          <div>
            <div style={{ textAlign: 'center', fontFamily: 'Outfit', fontWeight: 700, fontSize: '1rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              {isUserBatting ? '🏏 You\'re batting — pick your shot!' : '🎯 You\'re bowling — pick your delivery!'}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: '0.75rem', maxWidth: 460, margin: '0 auto' }}>
              {[1, 2, 3, 4, 5, 6].map(n => (
                <button key={n} className="hc-num-btn" onClick={() => playBall(n)}>{n}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ─── INNINGS BREAK ─────────────────────────────────────
  if (g.phase === 'break') {
    const firstBat = g.userBatting ? g.userTeam : g.cpuTeam
    const secondBat = g.userBatting ? g.cpuTeam : g.userTeam
    const fi = IPL_TEAMS[firstBat], si = IPL_TEAMS[secondBat]
    return (
      <div className="fade-in" style={{ textAlign: 'center' }}>
        <div className="hc-title">☕ Innings Break</div>
        <div className="scoreboard" style={{ maxWidth: 420, margin: '0 auto 1.25rem' }}>
          <div style={{ color: '#ffd700', fontFamily: 'Outfit', fontWeight: 700, marginBottom: '0.5rem' }}>1st Innings Complete</div>
          <div style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>{fi.emoji} {fi.short} scored</div>
          <div className="score-big">{g.inn1Runs}/{g.inn1Wkts}</div>
          <div className="score-label">({overs(g.inn1Balls)} overs)</div>
        </div>
        <div className="target-banner" style={{ maxWidth: 420, margin: '0 auto 1.25rem' }}>
          🎯 {si.emoji} {si.short} need {g.target} runs in {g.maxOvers} overs
        </div>
        <button className="btn-primary" style={{ padding: '0.85rem 2.5rem' }} onClick={() => update({ phase: 'playing', commentary: '' })}>
          ▶️ Start 2nd Innings
        </button>
      </div>
    )
  }

  // ─── RESULT ────────────────────────────────────────────
  if (g.phase === 'result') {
    const firstBat  = g.userBatting ? g.userTeam : g.cpuTeam
    const secondBat = g.userBatting ? g.cpuTeam  : g.userTeam
    const fi = IPL_TEAMS[firstBat], si = IPL_TEAMS[secondBat]
    const isUserWin = g.winner === g.userTeam
    const isTie     = g.winner === 'Tie'
    const winnerInfo = !isTie ? IPL_TEAMS[g.winner] : null

    let marginText = ''
    if (!isTie) {
      if (g.winner === secondBat) marginText = `by ${g.maxWkts - g.inn2Wkts} wicket${g.maxWkts - g.inn2Wkts !== 1 ? 's' : ''}`
      else marginText = `by ${g.inn1Runs - g.inn2Runs} run${g.inn1Runs - g.inn2Runs !== 1 ? 's' : ''}`
    }

    return (
      <div className="fade-in">
        <div className="hc-title">🏏 Match Result</div>

        {isTie
          ? <div className="winner-banner">🤝 It's a TIE! What a match!</div>
          : <div className="winner-banner">{isUserWin ? '🎉🏆' : '😞'} {winnerInfo?.emoji} {g.winner} wins {marginText}!</div>
        }

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.5rem' }}>
          <div className="scoreboard" style={{ textAlign: 'center' }}>
            <div style={{ color: '#9ca3af', fontSize: '0.78rem' }}>1ST INNINGS</div>
            <div style={{ fontSize: '1.2rem', margin: '0.3rem 0' }}>{fi.emoji} {fi.short}</div>
            <div className="score-big">{g.inn1Runs}/{g.inn1Wkts}</div>
            <div className="score-label">({overs(g.inn1Balls)} ov)</div>
          </div>
          <div className="scoreboard" style={{ textAlign: 'center' }}>
            <div style={{ color: '#9ca3af', fontSize: '0.78rem' }}>2ND INNINGS</div>
            <div style={{ fontSize: '1.2rem', margin: '0.3rem 0' }}>{si.emoji} {si.short}</div>
            <div className="score-big">{g.inn2Runs}/{g.inn2Wkts}</div>
            <div className="score-label">({overs(g.inn2Balls)} ov)</div>
          </div>
        </div>

        {/* Ball logs */}
        {[{ label: '1st Innings Ball Log', log: g.inn1Log }, { label: '2nd Innings Ball Log', log: g.inn2Log }].map(({ label, log }) => (
          <div key={label} className="card" style={{ marginBottom: '1rem' }}>
            <div className="section-title">{label}</div>
            <div className="ball-log">{log.map((b, i) => <BallBubble key={i} val={b} />)}</div>
          </div>
        ))}

        <button className="btn-primary" style={{ width: '100%', padding: '1rem' }} onClick={reset}>
          🔄 Play Again
        </button>
      </div>
    )
  }

  return null
}
