# Release Drafter Action

This project implements a GitHub Action for [Release Drafter](https://github.com/marketplace/actions/release-drafter), which automates the process of drafting release notes based on merged pull requests.

## Overview

Release Drafter helps you create release notes automatically by categorizing pull requests based on labels and generating a draft release in GitHub. This action runs on every push to the default branch and can be customized to fit your project's needs.

## Setup

To set up Release Drafter in your repository, follow these steps:

1. **Create a `.github/release-drafter.yml` file** in your repository with the desired configuration. This file defines how the release notes will be generated.

2. **Add the GitHub Actions workflow** by creating a `.github/workflows/release-drafter.yml` file. This file specifies when the action should run and the steps involved.

3. **Configure your pull request labels** to categorize changes. Release Drafter uses these labels to organize the release notes.

## Example Configuration

Here is an example of what your `.github/release-drafter.yml` might look like:

```yaml
name: Release Drafter

tag: auto
change-template: '- $TITLE @$AUTHOR'
categories:
  - title: '🚀 Features'
    labels: ['feature']
  - title: '🐛 Bug Fixes'
    labels: ['bug']
```

## Usage

Once set up, Release Drafter will automatically draft release notes based on the merged pull requests. You can find the draft release in the "Releases" section of your GitHub repository.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.