# Quantitative Research

This repository hosts a comprehensive framework for conducting quantitative research, featuring routines for data storage, strategy development, backtesting, and automated execution.

## Data Access

Data is stored on MongoDB Atlas, and access requires a URL connection string. For inquiries, please contact me at antognini.fosco@gmail.com.

## Project Structure

The project is structured into the following directories, each serving a specific purpose:

- [apps](https://github.com/foscoa/quantitative_research/tree/main/apps): Contains the backtest class and other research applications.
- [research](https://github.com/foscoa/quantitative_research/tree/main/research): Includes research scripts, with each trading strategy having its own file in the dedicated strategies directory.
- [routines](https://github.com/foscoa/quantitative_research/tree/main/routines): Holds routine files designed to execute jobs that periodically download, store data from various sources, or transform existing datasets.
- [utils](https://github.com/foscoa/quantitative_research/tree/main/utils): Contains utility functions used for querying and storing data to and from MongoDB.
- [execution_IBKR](https://github.com/foscoa/quantitative_research/tree/main/execution_IBKR): Contains the code for executing strategies at IBKR (Interactive Brokers).
