import React from 'react';
import styles from './StatsCard.module.scss';

interface StatsCardProps {
  title: string;
  value: number;
  color: string;
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, color }) => {
  return (
    <div className={styles.card} style={{ borderTop: `4px solid ${color}` }}>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.value} style={{ color }}>{value}</p>
    </div>
  );
};

export default StatsCard;