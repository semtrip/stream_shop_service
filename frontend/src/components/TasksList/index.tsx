import React from 'react';
import styles from './TasksList.module.scss';

interface Task {
  id: number;
  title: string;
  completed: boolean;
}

interface TasksListProps {
  tasks: Task[];
}

const TasksList: React.FC<TasksListProps> = ({ tasks }) => {
  return (
    <div className={styles.tasksList}>
      <h2 className={styles.title}>Мои задачи</h2>
      <ul className={styles.list}>
        {tasks.map(task => (
          <li key={task.id} className={styles.taskItem}>
            <input
              type="checkbox"
              checked={task.completed}
              readOnly
              className={styles.checkbox}
            />
            <span className={`${styles.taskText} ${task.completed ? styles.completed : ''}`}>
              {task.title}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TasksList;