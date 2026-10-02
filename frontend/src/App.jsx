import { useEffect, useRef, useState } from 'react'

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })
  const result = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(result.detail || `Request failed (${response.status})`)
  }
  return result
}

function CameraCapture({ onCapture, busy }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [active, setActive] = useState(false)
  const [snapshot, setSnapshot] = useState('')
  const [cameraError, setCameraError] = useState('')
  const [cameraFacing, setCameraFacing] = useState('user')

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  async function startCamera(facingMode = cameraFacing) {
    setCameraError('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Camera access is unavailable. Open this app on localhost in a supported browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
      })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      setSnapshot('')
      onCapture('')
      setActive(true)
    } catch (error) {
      setCameraError(
        error.name === 'NotAllowedError'
          ? 'Camera permission was denied. Allow camera access in your browser settings.'
          : 'No camera was found. Connect a camera and try again.',
      )
    }
  }

  function switchCamera() {
    const nextFacing = cameraFacing === 'user' ? 'environment' : 'user'
    setCameraFacing(nextFacing)

    if (!active) {
      return
    }

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setSnapshot('')
    onCapture('')
    startCamera(nextFacing)
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setActive(false)
    setSnapshot('')
    onCapture('')
  }

  function captureFrame() {
    const video = videoRef.current
    if (!video?.videoWidth) {
      setCameraError('The camera is still starting. Try again in a moment.')
      return
    }

    const scale = Math.min(1, 1280 / video.videoWidth)
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(video.videoWidth * scale)
    canvas.height = Math.round(video.videoHeight * scale)
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
    const image = canvas.toDataURL('image/jpeg', 0.88)
    setSnapshot(image)
    onCapture(image)
    setCameraError('')
  }

  function retake() {
    setSnapshot('')
    onCapture('')
  }

  return (
    <div className="camera-tool">
      <div className={`camera-view ${active ? 'camera-live' : ''}`}>
        <video ref={videoRef} autoPlay playsInline muted hidden={!active || Boolean(snapshot)} />
        {snapshot && <img src={snapshot} alt="Captured camera frame" />}
        {!active && !snapshot && (
          <div className="camera-placeholder">
            <span className="camera-icon" aria-hidden="true" />
            <span>Camera is off</span>
          </div>
        )}
        {active && !snapshot && <div className="face-guide" aria-hidden="true"><i /><i /><i /><i /></div>}
        {active && <span className="camera-live-label"><i /> LIVE</span>}
      </div>
      <div className="camera-controls">
        {!active ? (
          <button className="button-primary" type="button" onClick={() => startCamera()}>Start camera</button>
        ) : (
          <>
            {snapshot ? (
              <button className="button-primary" type="button" onClick={retake}>Retake photo</button>
            ) : (
              <button className="button-primary" type="button" onClick={captureFrame}>Capture frame</button>
            )}
            <button className="button-quiet" type="button" onClick={switchCamera}>
              {cameraFacing === 'user' ? 'Use rear camera' : 'Use front camera'}
            </button>
            <button className="button-quiet" type="button" onClick={stopCamera}>Stop camera</button>
          </>
        )}
        {busy && <span className="busy-note">Processing frame...</span>}
      </div>
      {cameraError && <p className="inline-error" role="alert">{cameraError}</p>}
    </div>
  )
}

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

function localDateKey(value = new Date()) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export default function App() {
  const [mode, setMode] = useState('attendance')
  const [students, setStudents] = useState([])
  const [records, setRecords] = useState([])
  const [todayCount, setTodayCount] = useState(0)
  const [capturedImage, setCapturedImage] = useState('')
  const [personName, setPersonName] = useState('')
  const [registrationNumber, setRegistrationNumber] = useState('')
  const [course, setCourse] = useState('')
  const [department, setDepartment] = useState('')
  const [yearSemester, setYearSemester] = useState('')
  const [consentGiven, setConsentGiven] = useState(false)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [apiOnline, setApiOnline] = useState(false)
  const [cameraVersion, setCameraVersion] = useState(0)
  const [directoryQuery, setDirectoryQuery] = useState('')
  const [activityFilter, setActivityFilter] = useState('today')
  const [refreshing, setRefreshing] = useState(false)

  async function loadDashboard() {
    const [people, attendance] = await Promise.all([
      apiRequest('/api/students'),
      apiRequest('/api/attendance'),
    ])
    setStudents(people)
    setRecords(attendance.records)
    setTodayCount(attendance.today_count)
    setApiOnline(true)
  }

  useEffect(() => {
    loadDashboard().catch(() => setApiOnline(false))
  }, [])

  const filteredStudents = students.filter((person) =>
    [person.name, person.registration_number, person.course, person.department, person.year_semester]
      .join(' ')
      .toLowerCase()
      .includes(directoryQuery.trim().toLowerCase()),
  )
  const visibleRecords = activityFilter === 'today'
    ? records.filter((record) => record.attendance_date === localDateKey())
    : records

  async function refreshDashboard() {
    setRefreshing(true)
    try {
      await loadDashboard()
      setFeedback({ type: 'notice', text: 'Attendance data refreshed.' })
    } catch (error) {
      setApiOnline(false)
      setFeedback({ type: 'error', text: `Refresh failed: ${error.message}` })
    } finally {
      setRefreshing(false)
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode)
    setCapturedImage('')
    setFeedback(null)
  }

  async function enrollPerson(event) {
    event.preventDefault()
    if (!capturedImage) {
      setFeedback({ type: 'error', text: 'Start the camera and capture a clear face first.' })
      return
    }
    if (!consentGiven) {
      setFeedback({ type: 'error', text: 'Confirm the person has agreed to biometric enrollment.' })
      return
    }

    setBusy(true)
    setFeedback(null)
    try {
      const person = await apiRequest('/api/students', {
        method: 'POST',
        body: JSON.stringify({
          name: personName,
          registration_number: registrationNumber,
          course,
          department,
          year_semester: yearSemester,
          image: capturedImage,
          consent_given: consentGiven,
        }),
      })
      await loadDashboard()
      setPersonName('')
      setRegistrationNumber('')
      setCourse('')
      setDepartment('')
      setYearSemester('')
      setConsentGiven(false)
      setCapturedImage('')
      setCameraVersion((version) => version + 1)
      setFeedback({ type: 'success', text: `${person.name} was enrolled successfully.` })
    } catch (error) {
      setFeedback({ type: 'error', text: error.message })
    } finally {
      setBusy(false)
    }
  }

  async function recognizePerson() {
    if (!capturedImage) {
      setFeedback({ type: 'error', text: 'Start the camera and capture a clear face first.' })
      return
    }

    setBusy(true)
    setFeedback(null)
    try {
      const result = await apiRequest('/api/attendance/recognize', {
        method: 'POST',
        body: JSON.stringify({ image: capturedImage }),
      })

      if (result.status === 'unrecognized') {
        setFeedback({ type: 'error', text: 'Face not recognized. Enroll this person or try another frame.' })
      } else if (result.status === 'already_checked_in') {
        setFeedback({ type: 'notice', text: `${result.student.name} (${result.student.registration_number}) is already checked in today.` })
        await loadDashboard()
        setCameraVersion((version) => version + 1)
      } else {
        setFeedback({ type: 'success', text: `Attendance marked for ${result.student.name} (${result.student.registration_number}).` })
        await loadDashboard()
        setCameraVersion((version) => version + 1)
      }
    } catch (error) {
      setFeedback({ type: 'error', text: error.message })
    } finally {
      setBusy(false)
    }
  }

  async function removePerson(person) {
    if (!window.confirm(`Remove ${person.name} and their attendance history?`)) return
    try {
      await apiRequest(`/api/students/${person.id}`, { method: 'DELETE' })
      await loadDashboard()
      setFeedback({ type: 'success', text: `${person.name} and their local records were removed.` })
    } catch (error) {
      setFeedback({ type: 'error', text: error.message })
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Attendance home">
          <span className="brand-mark">F</span>
          <span>Fieldnote <small>ATTENDANCE</small></span>
        </a>
        <span className={`connection-state ${apiOnline ? 'connected' : ''}`}>
          <i /> {apiOnline ? 'API connected' : 'API unavailable'}
        </span>
      </header>
      <main className="dashboard">
        <section className="page-heading">
          <div>
            <p className="eyebrow">LOCAL WORKSPACE <span>/</span> PEOPLE</p>
            <h1>Attendance</h1>
            <p className="intro">Enroll with consent, then check in using the camera.</p>
          </div>
          <div className="summary-stats" aria-label="Attendance summary">
            <div><strong>{todayCount}</strong><span>CHECKED IN TODAY</span></div>
            <div><strong>{students.length}</strong><span>ENROLLED PEOPLE</span></div>
          </div>
        </section>

        {!apiOnline && <div className="banner-error" role="alert">Backend unavailable. Start FastAPI on port 8001, then refresh.</div>}
        {feedback && <div className={`feedback ${feedback.type}`} role="status">{feedback.text}</div>}

        <div className="workspace-grid">
          <section className="workflow-panel" aria-label="Camera workflow">
            <div className="workflow-header">
              <div className="workflow-tabs" role="tablist" aria-label="Attendance actions">
                <button
                  className={mode === 'attendance' ? 'selected' : ''}
                  type="button"
                  role="tab"
                  aria-selected={mode === 'attendance'}
                  onClick={() => changeMode('attendance')}
                >Check in</button>
                <button
                  className={mode === 'enroll' ? 'selected' : ''}
                  type="button"
                  role="tab"
                  aria-selected={mode === 'enroll'}
                  onClick={() => changeMode('enroll')}
                >Enroll person</button>
              </div>
              <span className="camera-label">CAMERA INPUT</span>
            </div>

            <CameraCapture key={`${mode}-${cameraVersion}`} onCapture={setCapturedImage} busy={busy} />

            {mode === 'attendance' ? (
              <div className="workflow-action">
                <div>
                  <h2>Recognize and check in</h2>
                  <p>Keep one enrolled person centered in frame.</p>
                </div>
                <button className="button-primary" type="button" onClick={recognizePerson} disabled={busy || !capturedImage || !apiOnline}>
                  {busy ? 'Recognizing...' : 'Mark attendance'}
                </button>
              </div>
            ) : (
              <form className="enroll-form" onSubmit={enrollPerson}>
                <div className="registration-fields">
                  <div className="form-field form-field-wide">
                    <label htmlFor="person-name">Full name</label>
                    <input
                      id="person-name"
                      autoComplete="name"
                      maxLength={100}
                      value={personName}
                      onChange={(event) => setPersonName(event.target.value)}
                      placeholder="Enter person's name"
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="registration-number">Registration number</label>
                    <input
                      id="registration-number"
                      maxLength={40}
                      value={registrationNumber}
                      onChange={(event) => setRegistrationNumber(event.target.value)}
                      placeholder="e.g. REG-2026-001"
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="course">Course</label>
                    <input
                      id="course"
                      maxLength={120}
                      value={course}
                      onChange={(event) => setCourse(event.target.value)}
                      placeholder="e.g. Computer Science"
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="department">Department</label>
                    <input
                      id="department"
                      maxLength={120}
                      value={department}
                      onChange={(event) => setDepartment(event.target.value)}
                      placeholder="e.g. Computing"
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="year-semester">Year / semester</label>
                    <input
                      id="year-semester"
                      maxLength={40}
                      value={yearSemester}
                      onChange={(event) => setYearSemester(event.target.value)}
                      placeholder="e.g. Year 2 / Semester 1"
                      required
                    />
                  </div>
                </div>
                <label className="consent-row">
                  <input
                    type="checkbox"
                    checked={consentGiven}
                    onChange={(event) => setConsentGiven(event.target.checked)}
                  />
                  <span>I have this person's informed consent to store a face template for attendance.</span>
                </label>
                <button className="button-primary" type="submit" disabled={busy || !apiOnline}>
                  {busy ? 'Enrolling...' : 'Enroll person'}
                </button>
              </form>
            )}
            <p className="privacy-note">Only a face embedding is retained; the captured camera image is discarded after processing.</p>
          </section>

          <aside className="records-panel">
            <section className="people-section">
              <div className="section-heading">
                <div><p className="eyebrow">DIRECTORY</p><h2>Enrolled people</h2></div>
                <span className="count-label">{students.length}</span>
              </div>
              {students.length > 0 && (
                <label className="directory-search">
                  <span aria-hidden="true">Search</span>
                  <input
                    type="search"
                    aria-label="Search enrolled people"
                    placeholder="Find a person"
                    value={directoryQuery}
                    onChange={(event) => setDirectoryQuery(event.target.value)}
                  />
                </label>
              )}
              {students.length === 0 ? (
                <p className="empty-state">No one enrolled yet.</p>
              ) : (
                <ul className="people-list">
                  {filteredStudents.map((person) => (
                    <li key={person.id}>
                      <span className="person-monogram">{person.name.trim().charAt(0).toUpperCase()}</span>
                      <span className="person-name">
                        <strong>{person.name}</strong>
                        <small>{person.registration_number} / {person.course}</small>
                        <small>{person.department} / {person.year_semester}</small>
                      </span>
                      <button className="remove-button" type="button" onClick={() => removePerson(person)} aria-label={`Remove ${person.name}`} title={`Remove ${person.name}`}>
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {students.length > 0 && filteredStudents.length === 0 && (
                <p className="empty-state">No people match that search.</p>
              )}
            </section>

            <section className="activity-section">
              <div className="section-heading">
                <div><p className="eyebrow">LATEST RECORDS</p><h2>Recent attendance</h2></div>
                <button className="refresh-button" type="button" onClick={refreshDashboard} disabled={refreshing}>
                  {refreshing ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              <div className="activity-toolbar">
                <div className="activity-filters" role="group" aria-label="Filter attendance records">
                  <button className={activityFilter === 'today' ? 'selected' : ''} type="button" onClick={() => setActivityFilter('today')}>Today</button>
                  <button className={activityFilter === 'latest' ? 'selected' : ''} type="button" onClick={() => setActivityFilter('latest')}>Latest</button>
                </div>
                <span className="count-label">{visibleRecords.length} records</span>
              </div>
              {visibleRecords.length === 0 ? (
                <p className="empty-state">{activityFilter === 'today' ? 'No check-ins today yet.' : 'Check-ins will appear here.'}</p>
              ) : (
                <ul className="activity-list">
                  {visibleRecords.slice(0, 8).map((record) => (
                    <li key={record.id}>
                      <span className="activity-mark" aria-hidden="true" />
                      <span className="activity-name">
                        {record.name}
                        <small>{record.registration_number} / {record.course}</small>
                        <small>{record.department} / {record.year_semester}</small>
                      </span>
                      <time><small>{record.attendance_date}</small>{formatTime(record.checked_in_at)}</time>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </aside>
        </div>
      </main>

      <footer className="app-footer">
        <span>FACE ATTENDANCE <span className="footer-divider">/</span> LOCAL MODE</span>
        <span>Use only with informed consent. Remove templates when they are no longer needed.</span>
      </footer>
    </div>
  )
}