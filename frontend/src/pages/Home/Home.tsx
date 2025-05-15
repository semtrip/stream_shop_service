import React from 'react';
import Layout from '../../components/Layout';
import StatsCard from '../../components/StatsCard';
import TasksList from '../../components/TasksList';
import styles from '../../Home.module.scss';

const Home: React.FC = () => {
  // Пример данных
  const stats = [
    { title: 'Всего задач', value: 42, color: '#4CAF50' },
    { title: 'Выполнено', value: 24, color: '#2196F3' },
    { title: 'В процессе', value: 18, color: '#FFC107' }
  ];

  const tasks = [
    { id: 1, title: 'Завершить проект', completed: false },
    { id: 2, title: 'Провести встречу', completed: true },
    { id: 3, title: 'Написать документацию', completed: false }
  ];

  return (
    <Layout>
      <div className={styles.home}>
        <header className={styles.header}>
          <h1>Добро пожаловать в Task Manager</h1>
          <p>Управляйте своими задачами эффективно</p>
        </header>

        <div className={styles.statsContainer}>
          {stats.map((stat, index) => (
            <StatsCard 
              key={index}
              title={stat.title}
              value={stat.value}
              color={stat.color}
            />
          ))}
        </div>

        <div className={styles.tasksSection}>
          <TasksList tasks={tasks} />
        </div>
      </div>
    </Layout>
  );
};

export default Home;