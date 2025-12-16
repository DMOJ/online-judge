<h1 align="center">
  DMOJ: Modern Online Judge (Custom Fork)
</h1>
<p align="center">
  <a href="https://github.com/binghan1227/dmoj-web/actions?query=workflow%3Abuild">
    <img alt="Build Status" src="https://img.shields.io/github/actions/workflow/status/binghan1227/dmoj-web/build.yml?branch=customize"/>
  </a>
  <a href="LICENSE.md">
    <img alt="License" src="https://img.shields.io/github/license/binghan1227/dmoj-web"/>
  </a>
</p>

This is a customized fork of the [DMOJ: Modern Online Judge](https://dmoj.ca/), tailored with specific features for course management and enhanced user experience.

## New Features

This fork introduces several new capabilities designed for educational environments and streamlined administration.

### Interactive Online IDE
A dedicated coding environment (`/ide/`) that allows users to practice and test code without navigating to specific problems.
*   **Split-Pane Layout**: Side-by-side code editor, input area, and output display.
*   **Language Support**: Full syntax highlighting for all supported languages using ACE Editor.
*   **Smart Autosave**: Code and input are automatically saved to local storage, preventing data loss.
*   **Rate Limiting**: Custom time and memory constraints for IDE executions.

### Enhanced Problem Page
The problem view has been redesigned for better usability:
*   **Split-View Interface**: Resizable panes for the problem description and code editor.
*   **Fullscreen Mode**: A distraction-free coding experience.

### Administrative Tools
New commands and UI enhancements to simplify management:

*   **Bulk User Import**: Easily onboard students using `python manage.py import_users_csv`.
*   **Contest Data Export**:
    *   `export_contest_scores`: Export final scores to CSV.
    *   `export_contest_submissions`: Download all contest submissions as a ZIP archive.
*   **Admin UI Enhancements**:
    *   **Clone Problem**: One-click button to duplicate existing problems.
    *   **Edit Test Data**: Quick access link to manage test cases directly from the problem list.

### Problem Management
*   **Problem Templates**: Define starting code templates for specific languages to guide students.
*   **Test Case Access**: Configurable permissions to allow users to download failed test cases or tester files for debugging.

---

## Original DMOJ Features

*   **Multi-Language Support**: Run code in over 60 languages including C++, Java, Python, and Rust.
*   **Robust Judging**: Secure, scalable grading system with support for interactive problems and custom validators.
*   **Contest System**: heavily configurable with support for IOI, ICPC, and AtCoder formats.
*   **Rich Content**: Problems written in Markdown with LaTeX math support.
*   **Extensive Admin Interface**: Fine-grained permission controls, plagiarism detection, and more.

## Todo / Roadmap

- [ ] **Frontend Custom Grader Config**: Allow teachers to configure custom graders directly from the frontend without backend server access.
- [ ] **Comprehensive Contest Export**: Generate a PDF export containing all problem content, CSV for student scores, and zip for source code.
- [ ] **Frontend Student Import**: Add a user-friendly frontend interface for the `import_users_csv` command.
- [ ] **Enhanced Multi-Choice Support**: Improve configuration options for multi-choice problems.
- [ ] **Auto Indexing**: Automatically index problems and contests when creating new ones.

## Installation

Check out the install documentation at [docs.dmoj.ca](https://docs.dmoj.ca/#/site/installation) and my blog post at [squirrelstar.com](http://squirrelstar.com/posts/deploy-dmoj-for-cs-course/).

## License

This project is licensed under the same terms as the original DMOJ project.
