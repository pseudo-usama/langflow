from __future__ import annotations

import asyncio
import contextlib

from loguru import logger

from langflow.events.event_manager import EventManager, create_default_event_manager
from langflow.services.base import Service


class JobQueueService(Service):
    """Asynchronous service for managing job-specific queues and their associated tasks.

    This service allows clients to:
      - Create dedicated asyncio queues for individual jobs.
      - Associate each queue with an EventManager, enabling event-driven handling.
      - Launch and manage asynchronous tasks that process these job queues.
      - Safely clean up resources by cancelling active tasks and emptying queues.
      - Automatically perform periodic cleanup of inactive or completed job queues.

    Attributes:
        name (str): Unique identifier for the service.
        _queues (dict[str, tuple[asyncio.Queue, EventManager, asyncio.Task | None]]):
            Dictionary mapping job IDs to a tuple containing:
              * The job's asyncio.Queue instance.
              * The associated EventManager instance.
              * The asyncio.Task processing the job (if any).
        _cleanup_task (asyncio.Task | None): Background task for periodic cleanup.
        _closed (bool): Flag indicating whether the service is currently active.

    Example:
        service = JobQueueService()
        await service.start()
        queue, event_manager = service.create_queue("job123")
        service.start_job("job123", some_async_coroutine())
        # Retrieve and use the queue data as needed
        data = service.get_queue_data("job123")
        await service.cleanup_job("job123")
        await service.stop()
    """

    name = "job_queue_service"

    def __init__(self) -> None:
        """Initialize the JobQueueService.

        Sets up the internal registry for job queues, initializes the cleanup task, and sets the service state
        to active.
        """
        self._queues: dict[str, tuple[asyncio.Queue, EventManager, asyncio.Task | None]] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._closed = False

    async def start(self) -> None:
        """Start the JobQueueService and begin the periodic cleanup routine.

        This method marks the service as active and launches a background task that
        periodically checks and cleans up job queues whose tasks have been completed or cancelled.

        Raises:
            asyncio.CancelledError: If the background cleanup task is cancelled.
        """
        self._closed = False
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.debug("JobQueueService started: periodic cleanup task initiated.")

    async def stop(self) -> None:
        """Gracefully stop the JobQueueService by terminating background operations and cleaning up all resources.

        This coroutine performs the following steps:
            1. Marks the service as closed, preventing further job queue creation.
            2. Cancels the background periodic cleanup task and awaits its termination.
            3. Iterates over all registered job queues to clean up their resources—cancelling active tasks and
            clearing queued items.

        Raises:
            Exception: Propagates any exceptions encountered during the cancellation or termination of the cleanup task.
        """
        self._closed = True
        if self._cleanup_task:
            self._cleanup_task.cancel()
            await asyncio.wait([self._cleanup_task])
            if not self._cleanup_task.cancelled():
                exc = self._cleanup_task.exception()
                if exc is not None:
                    raise exc

        # Clean up each registered job queue.
        for job_id in list(self._queues.keys()):
            await self.cleanup_job(job_id)
        logger.info("JobQueueService stopped: all job queues have been cleaned up.")

    def create_queue(self, job_id: str) -> tuple[asyncio.Queue, EventManager]:
        """Create and register a new queue along with its corresponding event manager for a job.

        Args:
            job_id (str): Unique identifier for the job.

        Returns:
            tuple[asyncio.Queue, EventManager]: A tuple containing:
                - The asyncio.Queue instance for handling the job's tasks or messages.
                - The EventManager instance for event handling tied to the queue.

        Raises:
            ValueError: If a queue for the specified job_id already exists.
            RuntimeError: If the service is closed.
        """
        if job_id in self._queues:
            msg = f"Queue for job_id {job_id} already exists"
            logger.error(msg)
            raise ValueError(msg)

        if self._closed:
            msg = "Queue service is closed"
            logger.error(msg)
            raise RuntimeError(msg)

        main_queue: asyncio.Queue = asyncio.Queue()
        event_manager = create_default_event_manager(main_queue)

        # Register the queue without an active task.
        self._queues[job_id] = (main_queue, event_manager, None)
        logger.debug(f"Queue and event manager successfully created for job_id {job_id}")
        return main_queue, event_manager

    def start_job(self, job_id: str, task_coro) -> None:
        """Start an asynchronous task for a given job, replacing any existing active task.

        The method performs the following:
          - Verifies the presence of a registered queue for the job.
          - Cancels any currently running task associated with the job.
          - Launches a new asynchronous task using the provided coroutine.
          - Updates the internal registry with the new task.

        Args:
            job_id (str): Unique identifier for the job.
            task_coro: A coroutine representing the job's asynchronous task.

        Raises:
            ValueError: If no queue exists for the specified job_id.
        """
        if job_id not in self._queues:
            msg = f"No queue found for job_id {job_id}"
            logger.error(msg)
            raise ValueError(msg)

        main_queue, event_manager, existing_task = self._queues[job_id]

        if existing_task and not existing_task.done():
            logger.debug(f"Existing task for job_id {job_id} detected; cancelling it.")
            existing_task.cancel()

        # Initiate the new asynchronous task.
        task = asyncio.create_task(task_coro)
        self._queues[job_id] = (main_queue, event_manager, task)
        logger.debug(f"New task started for job_id {job_id}")

    def get_queue_data(self, job_id: str) -> tuple[asyncio.Queue, EventManager, asyncio.Task | None]:
        """Retrieve the complete data structure associated with a job's queue.

        Args:
            job_id (str): Unique identifier for the job.

        Returns:
            tuple[asyncio.Queue, EventManager, asyncio.Task | None]:
                A tuple containing the job's main queue, its linked event manager, and the associated task (if any).

        Raises:
            ValueError: If no queue is registered for the given job_id.
        """
        if job_id not in self._queues:
            msg = f"No queue found for job_id {job_id}"
            logger.error(msg)
            raise ValueError(msg)

        return self._queues[job_id]

    async def cleanup_job(self, job_id: str) -> None:
        """Clean up and release resources for a specific job.

        The cleanup process includes:
          1. Verifying if the job's queue is registered.
          2. Cancelling the running task (if active) and awaiting its termination.
          3. Clearing all items from the job's queue.
          4. Removing the job's entry from the internal registry.

        Args:
            job_id (str): Unique identifier for the job to be cleaned up.
        """
        if job_id not in self._queues:
            logger.debug(f"No queue found for job_id {job_id} during cleanup.")
            return

        logger.info(f"Commencing cleanup for job_id {job_id}")
        main_queue, event_manager, task = self._queues[job_id]

        # Cancel the associated task if it is still running.
        if task and not task.done():
            logger.debug(f"Cancelling active task for job_id {job_id}")
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            logger.debug(f"Task cancellation complete for job_id {job_id}")

        # If there is no active task or the task has completed, proceed with clearing the queue.
        if task is None or task.done():
            items_cleared = 0
            while not main_queue.empty():
                try:
                    main_queue.get_nowait()
                    items_cleared += 1
                except asyncio.QueueEmpty:
                    break

            logger.debug(f"Removed {items_cleared} items from queue for job_id {job_id}")
            # Delete the job entry from the registry.
            del self._queues[job_id]
            logger.info(f"Cleanup successful for job_id {job_id}: resources have been released.")
        else:
            logger.warning(f"Cleanup for job_id {job_id} deferred: task still running. Will retry in the next cycle.")

    async def _periodic_cleanup(self) -> None:
        """Execute a periodic task that cleans up completed or cancelled job queues.

        This internal coroutine continuously:
          - Sleeps for a fixed interval (60 seconds).
          - Initiates the cleanup of job queues by calling _cleanup_old_queues.
          - Monitors and logs any exceptions during the cleanup cycle.

        The loop terminates when the service is marked as closed.
        """
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Sleep for 60 seconds before next cleanup attempt.
                await self._cleanup_old_queues()
            except asyncio.CancelledError:
                logger.debug("Periodic cleanup task received cancellation signal.")
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Exception encountered during periodic cleanup: {exc}")

    async def _cleanup_old_queues(self) -> None:
        """Scan all registered job queues and clean up those with inactive tasks.

        For each job:
          - Check whether the associated task is either complete or cancelled.
          - If so, execute the cleanup_job method to release the job's resources.
        """
        for job_id in list(self._queues.keys()):
            _, _, task = self._queues[job_id]
            if task and (task.done() or task.cancelled()):
                logger.debug(f"Job queue for job_id {job_id} marked for cleanup.")
                await self.cleanup_job(job_id)
