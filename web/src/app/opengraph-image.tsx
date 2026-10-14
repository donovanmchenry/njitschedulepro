import { ImageResponse } from 'next/og';

export const alt = 'NJIT Schedule Pro — generate a class schedule that fits your availability';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function SocialImage() {
  return new ImageResponse(
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', background: '#030712', color: '#ffffff', padding: '80px' }}>
      <div style={{ display: 'flex', fontSize: 28, color: '#93c5fd', marginBottom: 32 }}>NJIT SCHEDULE PRO</div>
      <div style={{ display: 'flex', fontSize: 68, fontWeight: 700, lineHeight: 1.1 }}>Your classes. Your availability. Your schedule.</div>
      <div style={{ display: 'flex', fontSize: 30, color: '#d1d5db', marginTop: 36 }}>Generate schedules · Compare sections · Export to your calendar</div>
      <div style={{ display: 'flex', fontSize: 24, color: '#93c5fd', marginTop: 40 }}>www.njitschedulepro.com</div>
    </div>,
    size,
  );
}
