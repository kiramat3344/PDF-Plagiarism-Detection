
// const pdfFiles = document.getElementById("pdfFiles");
// const fileName = document.getElementById("fileName");

// const threshold = document.getElementById("threshold");
// const thresholdValue = document.getElementById("thresholdValue");

// const compareBtn = document.getElementById("compareBtn");
// const result = document.getElementById("result");

// // Show selected PDF files
// pdfFiles.addEventListener("change", function () {

//     const files = pdfFiles.files;

//     if (files.length === 0) {
//         fileName.textContent = "No files selected";
//         return;
//     }

//     fileName.textContent = "";

//     for (let file of files) {
//         fileName.innerHTML += file.name + "<br>";
//     }
// });

// // Update threshold percentage
// threshold.addEventListener("input", function () {

//     thresholdValue.textContent = threshold.value + "%";

// });

// // Compare button
// compareBtn.addEventListener("click", function () {

//     if (pdfFiles.files.length < 2) {
//         result.textContent = "Please select at least 2 PDF files.";
//         return;
//     }

//     result.textContent = "PDF files selected successfully! Comparison feature will be connected next.";

// });


// const pdfFiles = document.getElementById("pdfFiles");
// const fileName = document.getElementById("fileName");

// const threshold = document.getElementById("threshold");
// const thresholdValue = document.getElementById("thresholdValue");

// const compareBtn = document.getElementById("compareBtn");
// const result = document.getElementById("result");

// // Show selected files
// pdfFiles.addEventListener("change", function () {

//     fileName.innerHTML = "";

//     for (let file of pdfFiles.files) {
//         fileName.innerHTML += file.name + "<br>";
//     }

// });

// // Update threshold
// threshold.addEventListener("input", function () {

//     thresholdValue.textContent = threshold.value + "%";

// });

// // Upload PDF files to Flask
// compareBtn.addEventListener("click", async function () {

//     if (pdfFiles.files.length < 2) {
//         result.textContent = "Please select at least 2 PDF files.";
//         return;
//     }

//     const formData = new FormData();

//     for (let file of pdfFiles.files) {
//         formData.append("pdfFiles", file);
//     }

//     result.textContent = "Uploading PDF files...";

//     try {

//         const response = await fetch("/upload", {
//             method: "POST",
//             body: formData
//         });

//         const data = await response.json();

//         result.textContent = data.message;

//     } catch (error) {

//         result.textContent = "Upload failed. Please try again.";

//     }

// });




const pdfFiles = document.getElementById("pdfFiles");
const fileName = document.getElementById("fileName");

const threshold = document.getElementById("threshold");
const thresholdValue = document.getElementById("thresholdValue");

const compareBtn = document.getElementById("compareBtn");
const result = document.getElementById("result");

// Progress Bar Elements
const progressSection = document.getElementById("progressSection");
const progressText = document.getElementById("progressText");
const progressFill = document.getElementById("progressFill");
const progressPercent = document.getElementById("progressPercent");


// Show Selected PDF Files

pdfFiles.addEventListener("change", function () {

    fileName.innerHTML = "";

    if (pdfFiles.files.length > 50) {
        fileName.textContent = "Maximum 50 PDFs are allowed.";
        return;
    }

    for (let file of pdfFiles.files) {

        const item = document.createElement("p");
        item.textContent = file.name;

        fileName.appendChild(item);
    }
});


// Similarity Threshold

threshold.addEventListener("input", function () {
    thresholdValue.textContent = threshold.value + "%";
});


// Display Comparison Results

function displayResults(results) {

    result.innerHTML = "";

    const heading = document.createElement("h3");
    heading.textContent = "Comparison Results";

    result.appendChild(heading);

    results.forEach(item => {

        const isHigh =
            item.similarity >= Number(threshold.value);

        const card = document.createElement("div");

        card.className = isHigh
            ? "result-item high"
            : "result-item low";

        const names = document.createElement("h3");

        names.textContent =
            item.file1 + " vs " + item.file2;

        const percentage = document.createElement("div");

        percentage.className = "similarity";
        percentage.textContent = item.similarity + "%";

        const status = document.createElement("p");

        status.className = isHigh
            ? "high-status"
            : "low-status";

        status.textContent = isHigh
            ? "High Similarity"
            : "Low Similarity";

        card.appendChild(names);
        card.appendChild(percentage);
        card.appendChild(status);

        result.appendChild(card);
    });
}


// Compare PDFs

compareBtn.addEventListener("click", async function () {

    if (pdfFiles.files.length < 2) {
        result.textContent = "Please select at least 2 PDF files.";
        return;
    }

    if (pdfFiles.files.length > 50) {
        result.textContent = "Maximum 50 PDFs are allowed.";
        return;
    }

    const formData = new FormData();

    for (let file of pdfFiles.files) {
        formData.append("pdfFiles", file);
    }

    compareBtn.disabled = true;
    compareBtn.textContent = "Comparing...";

    progressSection.style.display = "block";

    progressFill.style.width = "0%";
    progressPercent.textContent = "0%";
    progressText.textContent = "Uploading and preparing PDFs...";

    result.textContent = "Starting comparison...";

    try {

        // Start Backend Comparison

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.job_id) {
            throw new Error(data.message || "Upload failed.");
        }

        const jobId = data.job_id;

        progressText.textContent = "Comparing PDF documents...";

        // Check Live Progress

        let completedResults = null;

        while (true) {

            const progressResponse = await fetch(
                `/progress/${jobId}`
            );

            const progressData = await progressResponse.json();

            if (!progressResponse.ok) {
                throw new Error(
                    progressData.message || "Progress loading failed."
                );
            }

            const completed = progressData.completed;
            const total = progressData.total;

            const percent = total > 0
                ? Math.round((completed / total) * 100)
                : 0;

            progressFill.style.width = percent + "%";
            progressPercent.textContent = percent + "%";

            progressText.textContent =
                `${completed} / ${total} comparisons completed`;

            if (progressData.status === "error") {
                throw new Error(
                    progressData.message || "Comparison failed."
                );
            }

            if (progressData.status === "completed") {

                completedResults = progressData.results;

                progressFill.style.width = "100%";
                progressPercent.textContent = "100%";

                progressText.textContent =
                    "All comparisons completed successfully!";

                break;
            }

            await new Promise(resolve => setTimeout(resolve, 700));
        }

        // Show Final Results

        displayResults(completedResults);

        loadDashboard();

    } catch (error) {

        result.textContent = error.message;

        progressText.textContent = "Comparison failed.";

    } finally {

        compareBtn.disabled = false;
        compareBtn.textContent = "Compare Documents";

    }

});


// Load Dashboard Statistics

async function loadDashboard() {

    try {

        const response = await fetch("/dashboard-stats");
        const data = await response.json();

        document.getElementById("totalComparisons").textContent =
            data.total;

        document.getElementById("highCount").textContent =
            data.high;

        document.getElementById("lowCount").textContent =
            data.low;

        document.getElementById("averageSimilarity").textContent =
            data.average + "%";

    } catch (error) {

        console.log("Dashboard loading failed:", error);

    }
}

loadDashboard();
