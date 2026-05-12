import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Scorecard from './pages/Scorecard'
import Predict from './pages/Predict'
import Players from './pages/Players'
import HandCricket from './pages/HandCricket'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/scorecard" element={<Scorecard />} />
          <Route path="/predict" element={<Predict />} />
          <Route path="/players" element={<Players />} />
          <Route path="/hand-cricket" element={<HandCricket />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
