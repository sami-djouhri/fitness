import { useState, useCallback } from 'react';
import type { MuscleGroupFreshness } from '../types';

interface Props {
  regions: MuscleGroupFreshness[];
  selectedRegion: string | null;
  onRegionClick: (regionId: string) => void;
  onMuscleClick?: (muscleName: string, regionId: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const LEGEND = [
  { color: '#22c55e', label: 'Frisch' },
  { color: '#4ade80', label: 'Bereit' },
  { color: '#facc15', label: 'Fällig' },
  { color: '#f97316', label: 'Überfällig' },
  { color: '#ef4444', label: 'Vernachlässigt' },
  { color: '#475569', label: 'Nie' },
];

const DEFAULT_COLOR = '#475569';
const BODY_COLOR = '#3a4252';

/* ------------------------------------------------------------------ */
/*  Muscle polygon definitions (from react-body-highlighter)           */
/*  ViewBox: 0 0 100 220                                               */
/* ------------------------------------------------------------------ */

interface MusclePoly {
  id: string;
  region: string;    // maps to our freshness region
  label: string;     // German tooltip
  points: string;    // SVG polygon points
}

// ── ANTERIOR (front) ──────────────────────────────────────────────

const FRONT_BODY: MusclePoly[] = [
  // Head (non-interactive, just for body shape)
  { id: 'head', region: '', label: 'Kopf',
    points: '42.4489796 2.85714286 40 11.8367347 42.0408163 19.5918367 46.122449 23.2653061 49.7959184 25.3061224 54.6938776 22.4489796 57.5510204 19.1836735 59.1836735 10.2040816 57.1428571 2.44897959 49.7959184 0' },

  // Neck
  { id: 'neck_l', region: '', label: 'Hals',
    points: '55.5102041 23.6734694 50.6122449 33.4693878 50.6122449 39.1836735 61.6326531 40 70.6122449 44.8979592 69.3877551 36.7346939 63.2653061 35.1020408 58.3673469 30.6122449' },
  { id: 'neck_r', region: '', label: 'Hals',
    points: '28.9795918 44.8979592 30.2040816 37.1428571 36.3265306 35.1020408 41.2244898 30.2040816 44.4897959 24.4897959 48.9795918 33.877551 48.5714286 39.1836735 37.9591837 39.5918367' },

  // Chest
  { id: 'chest_l', region: 'chest', label: 'Brust (L)',
    points: '51.8367347 41.6326531 51.0204082 55.1020408 57.9591837 57.9591837 67.755102 55.5102041 70.6122449 47.3469388 62.0408163 41.6326531' },
  { id: 'chest_r', region: 'chest', label: 'Brust (R)',
    points: '29.7959184 46.5306122 31.4285714 55.5102041 40.8163265 57.9591837 48.1632653 55.1020408 47.755102 42.0408163 37.5510204 42.0408163' },

  // Front Deltoids (inner/front portion)
  { id: 'front_delt_l', region: 'shoulders', label: 'Vordere Schulter (L)',
    points: '71.0204082 36.3265306 75.9183673 37.9591837 74.9 50.2 71.4285714 47.3469388 72.244898 42.8571429' },
  { id: 'front_delt_r', region: 'shoulders', label: 'Vordere Schulter (R)',
    points: '28.5714286 37.1428571 24.4897959 37.1428571 24.7 50.2 28.1632653 47.3469388 26.9387755 43.2653061' },

  // Side/Lateral Deltoids (outer/lateral portion)
  { id: 'side_delt_l', region: 'shoulders', label: 'Seitliche Schulter (L)',
    points: '75.9183673 37.9591837 79.1836735 41.2244898 79.5918367 47.755102 78.3673469 53.0612245 74.9 50.2' },
  { id: 'side_delt_r', region: 'shoulders', label: 'Seitliche Schulter (R)',
    points: '24.4897959 37.1428571 20.4081633 40.8163265 20 47.755102 21.2244898 53.0612245 24.7 50.2' },

  // Biceps: short head (inner)
  { id: 'biceps_short_l', region: 'biceps', label: 'Bizeps kurzer Kopf (L)',
    points: '71.4285714 49.3877551 70.2040816 54.6938776 76.3265306 66.122449 79.0 69.0 76.5 61.8 75.1 52.4' },
  { id: 'biceps_short_r', region: 'biceps', label: 'Bizeps kurzer Kopf (R)',
    points: '27.755102 49.3877551 28.9795918 53.877551 22.8571429 66.122449 20.4 68.8 22.9 61.0 24.1 52.7' },

  // Biceps: long head (outer)
  { id: 'biceps_long_l', region: 'biceps', label: 'Bizeps langer Kopf (L)',
    points: '75.1 52.4 76.5 61.8 79.0 69.0 81.6326531 71.8367347 82.8571429 68.9795918 78.7755102 55.5102041' },
  { id: 'biceps_long_r', region: 'biceps', label: 'Bizeps langer Kopf (R)',
    points: '24.1 52.7 22.9 61.0 20.4 68.8 17.9591837 71.4285714 16.7346939 68.1632653 20.4081633 55.9183673' },

  // Triceps (front view)
  { id: 'triceps_front_l', region: 'triceps', label: 'Trizeps (L)',
    points: '69.3877551 55.5102041 69.3877551 61.6326531 75.9183673 72.6530612 77.5510204 70.2040816 75.5102041 67.3469388' },
  { id: 'triceps_front_r', region: 'triceps', label: 'Trizeps (R)',
    points: '22.4489796 69.3877551 29.7959184 55.5102041 29.7959184 60.8163265 22.8571429 73.0612245' },

  // Forearm (front)
  { id: 'forearm_front_l1', region: 'biceps', label: 'Unterarm (L)',
    points: '84.4897959 69.7959184 83.2653061 73.4693878 80 73.0612245 95.1020408 98.3673469 100 100.408163 93.4693878 89.3877551 89.7959184 76.3265306' },
  { id: 'forearm_front_l2', region: 'biceps', label: 'Unterarm (L)',
    points: '77.5510204 72.244898 77.5510204 77.5510204 80.4081633 84.0816327 85.3061224 89.7959184 92.244898 101.22449 94.6938776 99.5918367' },
  { id: 'forearm_front_r1', region: 'biceps', label: 'Unterarm (R)',
    points: '6.12244898 88.5714286 10.2040816 75.1020408 14.6938776 70.2040816 16.3265306 74.2857143 19.1836735 73.4693878 4.48979592 97.5510204 0 100' },
  { id: 'forearm_front_r2', region: 'biceps', label: 'Unterarm (R)',
    points: '6.93877551 101.22449 13.4693878 90.6122611 18.7755102 84.0816327 21.6326531 77.1428571 21.2244898 71.8367347 4.89795918 98.7755102' },

  // Abs
  { id: 'abs_l', region: 'core', label: 'Bauch (L)',
    points: '56.3265306 59.1836735 57.9591837 64.0816327 58.3673469 77.9591837 58.3673469 92.6530612 56.3265306 98.3673469 55.1020408 104.081633 51.4285714 107.755102 51.0204082 84.4897959 50.6122449 67.3469388 51.0204082 57.1428571' },
  { id: 'abs_r', region: 'core', label: 'Bauch (R)',
    points: '43.6734694 58.7755102 48.5714286 57.1428571 48.9795918 67.3469388 48.5714286 84.4897959 48.1632653 107.346939 44.4897959 103.673469 40.8163265 91.4285714 40.8163265 78.3673469 41.2244898 64.4897959' },

  // Obliques
  { id: 'obliques_l', region: 'core', label: 'Seitl. Bauchmuskeln (L)',
    points: '68.5714286 63.2653061 67.3469388 57.1428571 58.7755102 59.5918367 60 64.0816327 60.4081633 83.2653061 65.7142857 78.7755102 66.5306122 69.7959184' },
  { id: 'obliques_r', region: 'core', label: 'Seitl. Bauchmuskeln (R)',
    points: '33.877551 78.3673469 33.0612245 71.8367347 31.0204082 63.2653061 32.244898 57.1428571 40.8163265 59.1836735 39.1836735 63.2653061 39.1836735 83.6734694' },

  // Abductors (outer thigh)
  { id: 'abductors_l', region: 'quads', label: 'Abduktoren (L)',
    points: '52.6530612 110.204082 54.2857143 124.897959 60 110.204082 62.0408163 100 64.8979592 94.2857143 60 92.6530612 56.7346939 104.489796' },
  { id: 'abductors_r', region: 'quads', label: 'Abduktoren (R)',
    points: '47.755102 110.612245 44.8979592 125.306122 42.0408163 115.918367 40.4081633 113.061224 39.5918367 107.346939 37.9591837 102.44898 34.6938776 93.877551 39.5918367 92.244898 41.6326531 99.1836735 43.6734694 105.306122' },

  // Quadriceps
  { id: 'quad_inner_r', region: 'quads', label: 'Quadrizeps innen (R)',
    points: '34.6938776 98.7755102 37.1428571 108.163265 37.1428571 127.755102 34.2857143 137.142857 31.0204082 132.653061 29.3877551 120 28.1632653 111.428571 29.3877551 100.816327 32.244898 94.6938776' },
  { id: 'quad_inner_l', region: 'quads', label: 'Quadrizeps innen (L)',
    points: '63.2653061 105.714286 64.4897959 100 66.9387755 94.6938776 70.2040816 101.22449 71.0204082 111.836735 68.1632653 133.061224 65.3061224 137.55102 62.4489796 128.571429 62.0408163 111.428571' },
  { id: 'quad_mid_r', region: 'quads', label: 'Quadrizeps mitte (R)',
    points: '38.7755102 129.387755 38.3673469 112.244898 41.2244898 118.367347 44.4897959 129.387755 42.8571429 135.102041 40 146.122449 36.3265306 146.530612 35.5102041 140' },
  { id: 'quad_mid_l', region: 'quads', label: 'Quadrizeps mitte (L)',
    points: '59.5918367 145.714286 55.5102041 128.979592 60.8163265 113.877551 61.2244898 130.204082 64.0816327 139.591837 62.8571429 146.530612' },
  { id: 'quad_outer_r', region: 'quads', label: 'Quadrizeps außen (R)',
    points: '32.6530612 138.367347 26.5306122 145.714286 25.7142857 136.734694 25.7142857 127.346939 26.9387755 114.285714 29.3877551 133.469388' },
  { id: 'quad_outer_l', region: 'quads', label: 'Quadrizeps außen (L)',
    points: '71.8367347 113.061224 73.877551 124.081633 73.877551 140.408163 72.6530612 145.714286 66.5306122 138.367347 70.2040816 133.469388' },

  // Knees (non-interactive)
  { id: 'knee_r', region: '', label: 'Knie',
    points: '33.877551 140 34.6938776 143.265306 35.5102041 147.346939 36.3265306 151.020408 35.1020408 156.734694 29.7959184 156.734694 27.3469388 152.653061 27.3469388 147.346939 30.2040816 144.081633' },
  { id: 'knee_l', region: '', label: 'Knie',
    points: '65.7142857 140 72.244898 147.755102 72.244898 152.244898 69.7959184 157.142857 64.8979592 156.734694 62.8571429 151.020408' },

  // Calves (front)
  { id: 'calf_front_l1', region: 'calves', label: 'Wade (L)',
    points: '71.4285714 160.408163 73.4693878 153.469388 76.7346939 161.22449 79.5918367 167.755102 78.3673469 187.755102 79.5918367 195.510204 74.6938776 195.510204' },
  { id: 'calf_front_l2', region: 'calves', label: 'Wade (L)',
    points: '72.6530612 195.102041 69.7959184 159.183673 65.3061224 158.367347 64.0816327 162.44898 64.0816327 165.306122 65.7142857 177.142857' },
  { id: 'calf_front_r1', region: 'calves', label: 'Wade (R)',
    points: '24.8979592 194.693878 27.755102 164.897959 28.1632653 160.408163 26.122449 154.285714 24.8979592 157.55102 22.4489796 161.632653 20.8163265 167.755102 22.0408163 188.163265 20.8163265 195.510204' },
  { id: 'calf_front_r2', region: 'calves', label: 'Wade (R)',
    points: '35.5102041 158.367347 35.9183673 162.44898 35.9183673 166.938776 35.1020408 172.244898 35.1020408 176.734694 32.244898 182.040816 30.6122449 187.346939 26.9387755 194.693878 27.3469388 187.755102 28.1632653 180.408163 28.5714286 175.510204 28.9795918 169.795918 29.7959184 164.081633 30.2040816 158.77551' },
];

// ── POSTERIOR (back) ──────────────────────────────────────────────

const BACK_BODY: MusclePoly[] = [
  // Head
  { id: 'head_back', region: '', label: 'Kopf',
    points: '50.6382979 0 45.9574468 0.85106383 40.8510638 5.53191489 40.4255319 12.7659574 45.106383 20 55.7446809 20 59.1489362 13.6170213 59.5744681 4.68085106 55.7446809 1.27659574' },

  // Trapezius
  { id: 'trap_l', region: 'traps', label: 'Trapez (L)',
    points: '44.6808511 21.7021277 47.6595745 21.7021277 47.2340426 38.2978723 47.6595745 64.6808511 38.2978723 53.1914894 35.3191489 40.8510638 31.0638298 36.5957447 39.1489362 33.1914894 43.8297872 27.2340426' },
  { id: 'trap_r', region: 'traps', label: 'Trapez (R)',
    points: '52.3404255 21.7021277 55.7446809 21.7021277 56.5957447 27.2340426 60.8510638 32.7659574 68.9361702 36.5957447 64.6808511 40.4255319 61.7021277 53.1914894 52.3404255 64.6808511 53.1914894 38.2978723' },

  // Rear Deltoids (inner/posterior portion)
  { id: 'rear_delt_l', region: 'shoulders', label: 'Hintere Schulter (L)',
    points: '29.3617021 37.0212766 22.9787234 39.1489362 24.2553191 49.3617021 27.2340426 46.3829787' },
  { id: 'rear_delt_r', region: 'shoulders', label: 'Hintere Schulter (R)',
    points: '71.0638298 37.0212766 78.2978723 39.5744681 74.893617 48.9361702 72.3404255 45.106383' },

  // Side/Lateral Deltoids (back view: outer portion)
  { id: 'side_delt_back_l', region: 'shoulders', label: 'Seitliche Schulter (L)',
    points: '22.9787234 39.1489362 17.4468085 44.2553191 18.2978723 53.6170213 24.2553191 49.3617021' },
  { id: 'side_delt_back_r', region: 'shoulders', label: 'Seitliche Schulter (R)',
    points: '78.2978723 39.5744681 82.5531915 44.6808511 81.7021277 53.6170213 74.893617 48.9361702' },

  // Upper Back
  { id: 'upper_back_l', region: 'back', label: 'Oberer Rücken (L)',
    points: '31.0638298 38.7234043 28.0851064 48.9361702 28.5106383 55.3191489 34.0425532 75.3191489 47.2340426 71.0638298 47.2340426 66.3829787 36.5957447 54.0425532 33.6170213 41.2765957' },
  { id: 'upper_back_r', region: 'back', label: 'Oberer Rücken (R)',
    points: '68.9361702 38.7234043 71.9148936 49.3617021 71.4893617 56.1702128 65.9574468 75.3191489 52.7659574 71.0638298 52.7659574 66.3829787 63.4042553 54.4680851 66.3829787 41.7021277' },

  // Triceps: lateral head (outer)
  { id: 'triceps_lat_l', region: 'triceps', label: 'Trizeps lateral (L)',
    points: '26.8085106 49.787234 17.8723404 55.7446809 14.4680851 72.3404255 16.5957447 81.7021277 21.7021277 63.8297872 26.8085106 55.7446809' },
  { id: 'triceps_lat_r', region: 'triceps', label: 'Trizeps lateral (R)',
    points: '73.6170213 50.212766 82.1276596 55.7446809 85.9574968 73.1914894 83.4042553 82.1276596 77.8723404 62.9787234 73.1914894 55.7446809' },

  // Triceps: long head (inner)
  { id: 'triceps_long_l', region: 'triceps', label: 'Trizeps langer Kopf (L)',
    points: '26.8085106 58.2978723 26.8085106 68.5106383 22.9787234 75.3191489 19.1489362 77.4468085 22.5531915 65.5319149' },
  { id: 'triceps_long_r', region: 'triceps', label: 'Trizeps langer Kopf (R)',
    points: '72.7659574 58.2978723 77.0212766 64.6808511 80.4255319 77.4468085 76.5957447 75.3191489 72.7659574 68.9361702' },

  // Forearm (back)
  { id: 'forearm_back_l1', region: 'triceps', label: 'Unterarm (L)',
    points: '13.6170213 75.7446809 8.93617021 83.8297872 6.80851064 93.6170213 0 106.382979 3.82978723 104.255319 12.3404255 88.5106383 15.7446809 82.9787234' },
  { id: 'forearm_back_l2', region: 'triceps', label: 'Unterarm (L)',
    points: '18.7234043 79.5744681 22.1276596 77.8723404 20.8510638 84.2553191 9.36170213 102.978723 6.80851064 108.510638 5.10638298 104.680851' },
  { id: 'forearm_back_r1', region: 'triceps', label: 'Unterarm (R)',
    points: '86.3829787 75.7446809 91.0638298 83.4042553 93.1914894 94.0425532 100 106.382979 96.1702128 104.255319 88.0851064 89.3617021 84.2553191 83.8297872' },
  { id: 'forearm_back_r2', region: 'triceps', label: 'Unterarm (R)',
    points: '81.2765957 79.5744681 77.4468085 77.8723404 79.1489362 84.6808511 91.0638298 103.829787 93.1914894 108.93617 94.4680851 104.680851' },

  // Lower Back
  { id: 'lower_back_l', region: 'back', label: 'Unterer Rücken (L)',
    points: '47.6595745 72.7659574 34.4680851 77.0212766 35.3191489 83.4042553 49.3617021 102.12766 46.8085106 82.9787234' },
  { id: 'lower_back_r', region: 'back', label: 'Unterer Rücken (R)',
    points: '52.3404255 72.7659574 65.5319149 77.0212766 64.6808511 83.4042553 50.6382979 102.12766 53.1914894 83.8297872' },

  // Gluteal
  { id: 'glute_l', region: 'hamstrings', label: 'Gesäß (L)',
    points: '44.6808511 99.5744681 30.212766 108.510638 29.787234 118.723404 31.4893617 125.957447 47.2340426 121.276596 49.3617021 114.893617' },
  { id: 'glute_r', region: 'hamstrings', label: 'Gesäß (R)',
    points: '55.3191489 99.1489362 51.0638298 114.468085 52.3404255 120.851064 68.0851064 125.957447 69.787234 119.148936 69.3617021 108.510638' },

  // Adductors (inner thigh, back view)
  { id: 'adductor_l', region: 'quads', label: 'Adduktoren (L)',
    points: '48.0851064 122.978723 44.6808511 122.978723 41.2765957 125.531915 45.106383 144.255319 48.5106383 135.744681 48.9361702 129.361702' },
  { id: 'adductor_r', region: 'quads', label: 'Adduktoren (R)',
    points: '51.9148936 122.553191 55.7446809 123.404255 59.1489362 125.957447 54.893617 144.255319 51.9148936 136.170213 51.0638298 129.361702' },

  // Hamstrings
  { id: 'hamstring_outer_l', region: 'hamstrings', label: 'Beinbizeps außen (L)',
    points: '28.9361702 122.12766 31.0638298 129.361702 36.5957447 125.957447 35.3191489 135.319149 34.4680851 150.212766 29.3617021 158.297872 28.9361702 146.808511 27.6595745 141.276596 27.2340426 131.489362' },
  { id: 'hamstring_outer_r', region: 'hamstrings', label: 'Beinbizeps außen (R)',
    points: '71.4893617 121.702128 69.3617021 128.93617 63.8297872 125.957447 65.5319149 136.595745 66.3829787 150.212766 71.0638298 158.297872 71.4893617 147.659574 72.7659574 142.12766 73.6170213 131.914894' },
  { id: 'hamstring_inner_l', region: 'hamstrings', label: 'Beinbizeps innen (L)',
    points: '38.7234043 125.531915 44.2553191 145.957447 40.4255319 166.808511 36.1702128 152.765957 37.0212766 135.319149' },
  { id: 'hamstring_inner_r', region: 'hamstrings', label: 'Beinbizeps innen (R)',
    points: '61.7021277 125.531915 63.4042553 136.170213 64.2553191 153.191489 60 166.808511 56.1702128 146.382979' },

  // Knees (non-interactive)
  { id: 'knee_back_l', region: '', label: 'Knie',
    points: '34.4680851 153.191489 31.0638298 159.148936 33.6170213 166.382979 37.4468085 162.553191' },
  { id: 'knee_back_r', region: '', label: 'Knie',
    points: '66.3829787 153.617021 62.9787234 162.978723 66.8085106 166.382979 69.3617021 159.148936' },

  // Calves (back)
  { id: 'calf_back_l1', region: 'calves', label: 'Wade (L)',
    points: '29.3617021 160.425532 28.5106383 167.234043 24.6808511 179.574468 23.8297872 192.765957 25.5319149 197.021277 28.5106383 193.191489 29.787234 180 31.9148936 171.06383 31.9148936 166.808511' },
  { id: 'calf_back_l2', region: 'calves', label: 'Wade (L)',
    points: '37.4468085 165.106383 35.3191489 167.659574 33.1914894 171.914894 31.0638298 180.425532 30.212766 191.914894 34.0425532 200 38.7234043 190.638298 39.1489362 168.93617' },
  { id: 'calf_back_r1', region: 'calves', label: 'Wade (R)',
    points: '62.9787234 165.106383 61.2765957 168.510638 61.7021277 190.638298 66.3829787 199.574468 70.6382979 191.914894 68.9361702 179.574468 66.8085106 170.212766' },
  { id: 'calf_back_r2', region: 'calves', label: 'Wade (R)',
    points: '70.6382979 160.425532 72.3404255 168.510638 75.7446809 179.148936 76.5957447 192.765957 74.4680851 196.595745 72.3404255 193.617021 70.6382979 179.574468 68.0851064 168.085106' },

  // Soleus
  { id: 'soleus_l', region: 'calves', label: 'Schollenmuskel (L)',
    points: '28.5106383 195.744681 30.212766 195.744681 33.6170213 201.702128 30.6382979 220 28.5106383 213.617021 26.8085106 198.297872' },
  { id: 'soleus_r', region: 'calves', label: 'Schollenmuskel (R)',
    points: '69.787234 195.744681 71.9148936 195.744681 73.6170213 198.297872 71.9148936 213.191489 70.212766 219.574468 67.2340426 202.12766' },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function MuscleMap({ regions, selectedRegion, onRegionClick, onMuscleClick }: Props) {
  const [view, setView] = useState<'front' | 'back'>('front');
  const [hoveredMuscle, setHoveredMuscle] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ label: string; x: number; y: number } | null>(null);

  const colorMap: Record<string, string> = {};
  const daysMap: Record<string, number | null> = {};
  for (const r of regions) {
    colorMap[r.region] = r.color;
    daysMap[r.region] = r.days_since_trained;
  }

  const muscles = view === 'front' ? FRONT_BODY : BACK_BODY;

  const getFill = useCallback((region: string) => {
    if (!region) return BODY_COLOR;
    return colorMap[region] || DEFAULT_COLOR;
  }, [colorMap]);

  const shadeBias = useCallback((muscleId: string): number => {
    if (/short|inner|long_l|long_r|lat_l|lat_r/.test(muscleId)) return -0.08;
    return 0.0;
  }, []);

  const getOpacity = useCallback((region: string, muscleId: string) => {
    if (!region) return 0.6;
    if (hoveredMuscle === muscleId) return 1;
    if (selectedRegion === region) return 0.95 + shadeBias(muscleId);
    return 0.5 + shadeBias(muscleId);
  }, [hoveredMuscle, selectedRegion, shadeBias]);

  const getStroke = useCallback((region: string, muscleId: string) => {
    if (!region) return 'rgba(255,255,255,0.05)';
    if (hoveredMuscle === muscleId) return '#fff';
    if (selectedRegion === region) return '#60a5fa';
    return 'rgba(0,0,0,0.45)';
  }, [hoveredMuscle, selectedRegion]);

  const getStrokeWidth = useCallback((region: string, muscleId: string) => {
    if (!region) return 0.2;
    if (hoveredMuscle === muscleId) return 0.8;
    if (selectedRegion === region) return 0.5;
    return 0.4;
  }, [hoveredMuscle, selectedRegion]);

  const getDaysText = (region: string): string => {
    const days = daysMap[region];
    if (days === null || days === undefined) return 'Noch nie trainiert';
    if (days === 0) return 'Heute trainiert';
    if (days === 1) return 'Gestern trainiert';
    return `Vor ${days} Tagen`;
  };

  const handleMouseEnter = (muscle: MusclePoly, e: React.MouseEvent) => {
    if (!muscle.region) return;
    setHoveredMuscle(muscle.id);
    const rect = (e.currentTarget as SVGElement).closest('svg')?.getBoundingClientRect();
    if (rect) {
      const daysInfo = getDaysText(muscle.region);
      setTooltip({
        label: `${muscle.label}: ${daysInfo}`,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top - 28,
      });
    }
  };

  const handleMouseMove = (muscle: MusclePoly, e: React.MouseEvent) => {
    if (!muscle.region) return;
    const rect = (e.currentTarget as SVGElement).closest('svg')?.getBoundingClientRect();
    if (rect) {
      const daysInfo = getDaysText(muscle.region);
      setTooltip({
        label: `${muscle.label}: ${daysInfo}`,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top - 28,
      });
    }
  };

  const handleMouseLeave = () => {
    setHoveredMuscle(null);
    setTooltip(null);
  };

  const handleClick = (muscle: MusclePoly) => {
    if (!muscle.region) return;
    if (onMuscleClick) {
      onMuscleClick(muscle.id, muscle.region);
    } else {
      onRegionClick(muscle.region);
    }
  };

  return (
    <div className="muscle-map-container">
      {/* View toggle */}
      <div className="muscle-map-toggle">
        <button
          className={`toggle-btn ${view === 'front' ? 'active' : ''}`}
          onClick={() => setView('front')}
        >
          Vorne
        </button>
        <button
          className={`toggle-btn ${view === 'back' ? 'active' : ''}`}
          onClick={() => setView('back')}
        >
          Hinten
        </button>
      </div>

      {/* SVG Body */}
      <div className="muscle-map-body" style={{ position: 'relative' }}>
        <svg viewBox="-2 -2 104 224">
          {/* Muscle groups */}
          {muscles.map(muscle => (
            <polygon
              key={muscle.id}
              points={muscle.points}
              data-region={muscle.region}
              data-muscle={muscle.id}
              data-selected={muscle.region && selectedRegion === muscle.region ? 'true' : undefined}
              fill={getFill(muscle.region)}
              opacity={getOpacity(muscle.region, muscle.id)}
              stroke={getStroke(muscle.region, muscle.id)}
              strokeWidth={getStrokeWidth(muscle.region, muscle.id)}
              strokeLinejoin="round"
              style={{
                cursor: muscle.region ? 'pointer' : 'default',
                transition: 'opacity 0.15s, stroke 0.15s, fill 0.15s',
              }}
              onMouseEnter={(e) => handleMouseEnter(muscle, e)}
              onMouseMove={(e) => handleMouseMove(muscle, e)}
              onMouseLeave={handleMouseLeave}
              onClick={() => handleClick(muscle)}
            />
          ))}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="muscle-tooltip"
            style={{
              left: tooltip.x,
              top: tooltip.y,
              transform: 'translateX(-50%)',
            }}
          >
            {tooltip.label}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="muscle-legend">
        {LEGEND.map(({ color, label }) => (
          <div key={color} className="muscle-legend-item">
            <span className="muscle-legend-dot" style={{ background: color }} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
