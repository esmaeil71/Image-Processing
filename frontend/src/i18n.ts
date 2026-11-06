import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      app_title: "MedImage Studio",
      disclaimer:
        "For research and specialist review only — not for independent diagnosis or treatment.",
      login: "Sign in",
      email: "Email",
      password: "Password",
      studies: "Studies",
      upload: "Upload",
      logout: "Sign out",
      run_model: "Run segmentation job",
      language: "Language",
      nifti_viewer: "NIfTI viewer (Niivue)",
      orthanc_viewer: "DICOM (Orthanc / DICOMweb)",
    },
  },
  fa: {
    translation: {
      app_title: "استودیو مدایمیج",
      disclaimer:
        "صرفاً برای پژوهش و بازبینی متخصص؛ برای تشخیص یا درمان مستقل استفاده نشود.",
      login: "ورود",
      email: "ایمیل",
      password: "رمز عبور",
      studies: "مطالعات",
      upload: "بارگذاری",
      logout: "خروج",
      run_model: "اجرای قطعه‌بندی",
      language: "زبان",
      nifti_viewer: "نمایشگر NIfTI (Niivue)",
      orthanc_viewer: "DICOM (Orthanc / DICOMweb)",
    },
  },
};

void i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem("lng") || "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
